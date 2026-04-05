"""Session endpoints: CRUD + WebSocket voice pipeline.

REST:
  POST   /api/v1/sessions          — create session
  GET    /api/v1/sessions          — list user sessions
  GET    /api/v1/sessions/{id}     — session detail
  PATCH  /api/v1/sessions/{id}     — end session

WebSocket:
  WS /api/v1/sessions/{id}/voice  — voice pipeline (auth via ?token=<access_token>)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.interview_session import InterviewSession, SessionStatus
from app.models.question import Question
from app.models.session_metrics import SessionMetrics as _SessionMetrics
from app.models.user import User
from app.schemas.session import (
    JdAnalysisRequest,
    JdAnalysisResponse,
    JdFocusArea,
    SessionCreate,
    SessionDetail,
    SessionEnd,
    SessionResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.auth.jwt_utils import decode_token
from app.services.byok import decrypt_byok_keys
from app.services.memory.loader import load_memory_context
from app.services.voice.pipeline import VoicePipeline
from app.services.voice.prompts import build_candidate_context_block
from app.services.voice.provider_factory import ProviderFactory

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


# ── REST CRUD ──────────────────────────────────────────────────────────────────


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    """Create a new interview session.

    Business model (open-source portfolio project):
      - First 2 sessions are free — the platform covers all AI costs.
      - From session 3 onwards the user must supply their own Anthropic key.
        Deepgram (STT) and ElevenLabs (TTS) remain covered by the platform.
      - Gate is skipped when the platform itself has ANTHROPIC_API_KEY set
        (e.g. in development or on the host's own Fly.io deployment), so the
        project author can always test without adding BYOK keys.
    """
    session_type = body.type

    # Count existing sessions for this user
    count_result = await db.execute(
        select(InterviewSession).where(InterviewSession.user_id == current_user.id)
    )
    existing_sessions = count_result.scalars().all()
    session_count = len(existing_sessions)

    is_first_session = session_count == 0

    # Auto-route first-ever session to diagnostic mode
    if is_first_session and session_type != "diagnostic":
        logger.info("sessions.first_session_forced_diagnostic", user_id=str(current_user.id))
        session_type = "diagnostic"

    # From session 3 onwards, require user's own Anthropic key —
    # unless the platform already has a key configured (dev / hosted mode).
    free_session_limit = 2
    if session_count >= free_session_limit:
        byok = current_user.byok_keys or {}
        has_user_key = "anthropic" in byok
        has_platform_key = bool(settings.anthropic_api_key)
        if not has_user_key and not has_platform_key:
            logger.info(
                "sessions.byok_required",
                user_id=str(current_user.id),
                session_count=session_count,
            )
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    "Your 2 free sessions have been used. "
                    "Add your Anthropic API key in Settings to continue — "
                    "get one free at console.anthropic.com. "
                    "Deepgram and ElevenLabs are still covered by the platform."
                ),
            )

    session = InterviewSession(
        user_id=current_user.id,
        type=session_type,
        interview_type=body.interview_type,
        quality_profile=body.quality_profile,
        voice_id=body.voice_id,
        persona=body.persona,
        company=body.company,
        focus_skill=body.focus_skill,
        duration_limit_minutes=body.duration_limit_minutes,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(
        "sessions.created",
        session_id=str(session.id),
        type=session_type,
        profile=body.quality_profile,
    )
    return SessionResponse.model_validate(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[SessionResponse]:
    """List the authenticated user's sessions, newest first."""
    result = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    sessions = result.scalars().all()
    return [SessionResponse.model_validate(s) for s in sessions]


# ── POST /api/v1/sessions/analyze-jd ─────────────────────────────────────────
# NOTE: must be declared before /{session_id} routes so FastAPI doesn't treat
# "analyze-jd" as a session_id path parameter.

_JD_TOOL_SCHEMA: dict = {
    "name": "analyze_jd",
    "description": "Extract structured information from a job description",
    "input_schema": {
        "type": "object",
        "required": [
            "skills_required",
            "skills_nice_to_have",
            "seniority",
            "role_type",
            "suggested_session_type",
            "suggested_company",
            "focus_areas",
            "coaching_note",
        ],
        "properties": {
            "skills_required": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Skills explicitly required in the JD (max 10)",
            },
            "skills_nice_to_have": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Skills listed as nice-to-have or preferred (max 8)",
            },
            "seniority": {
                "type": "string",
                "enum": ["junior", "mid", "senior", "staff", "principal", "unknown"],
            },
            "role_type": {
                "type": "string",
                "enum": [
                    "backend",
                    "frontend",
                    "fullstack",
                    "ml",
                    "data",
                    "mobile",
                    "devops",
                    "other",
                ],
            },
            "suggested_session_type": {
                "type": "string",
                "enum": [
                    "behavioral",
                    "system_design",
                    "coding_discussion",
                    "negotiation",
                    "debrief",
                ],
                "description": "Which interview type to practice first for this role",
            },
            "suggested_company": {
                "type": ["string", "null"],
                "description": "Detected company slug (google/meta/amazon/microsoft/apple/netflix/uber/stripe/linkedin/airbnb/nvidia/spotify) or null",
            },
            "focus_areas": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "required": ["area", "reason", "priority"],
                    "properties": {
                        "area": {"type": "string"},
                        "reason": {"type": "string"},
                        "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                    },
                },
            },
            "coaching_note": {
                "type": "string",
                "description": "1-2 sentence preparation tip specific to this role",
            },
        },
    },
}

_JD_SYSTEM = (
    "You are an expert technical recruiter. Analyze job descriptions and extract "
    "structured information to help candidates prepare for interviews. "
    "Be specific and accurate. Only include skills explicitly mentioned in the JD."
)

_VALID_COMPANIES = frozenset(
    [
        "google",
        "meta",
        "amazon",
        "microsoft",
        "apple",
        "netflix",
        "uber",
        "stripe",
        "linkedin",
        "airbnb",
        "nvidia",
        "spotify",
    ]
)


@router.post("/analyze-jd", response_model=JdAnalysisResponse)
async def analyze_jd(
    body: JdAnalysisRequest,
    current_user: CurrentUser,
) -> JdAnalysisResponse:
    """Analyze a job description and extract structured preparation guidance.

    Uses Claude Haiku via tool_use for structured JSON extraction.
    Cost: ~$0.001/call. No DB write — result returned directly.
    """
    import time

    from anthropic import AsyncAnthropic

    api_key = settings.anthropic_api_key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service not configured.",
        )

    client = AsyncAnthropic(api_key=api_key)
    t0 = time.monotonic()

    try:
        response = await client.messages.create(  # type: ignore[call-overload]
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=_JD_SYSTEM,
            tools=[_JD_TOOL_SCHEMA],  # type: ignore[list-item]
            tool_choice={"type": "tool", "name": "analyze_jd"},  # type: ignore[arg-type]
            messages=[
                {
                    "role": "user",
                    "content": f"Analyze this job description:\n\n{body.jd_text[:6000]}",
                }
            ],
        )
    except Exception as exc:
        logger.error("jd_analysis.llm_failed", error=str(exc), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Analysis failed."
        )

    latency_ms = int((time.monotonic() - t0) * 1000)

    tool_block = next(
        (b for b in response.content if b.type == "tool_use" and b.name == "analyze_jd"),
        None,
    )
    if not tool_block:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="LLM did not return structured output."
        )

    data = tool_block.input

    raw_company = (data.get("suggested_company") or "").lower().strip()
    suggested_company = raw_company if raw_company in _VALID_COMPANIES else None

    focus_areas = [
        JdFocusArea(
            area=fa.get("area", ""),
            reason=fa.get("reason", ""),
            priority=fa.get("priority", "medium"),
        )
        for fa in (data.get("focus_areas") or [])
    ]

    logger.info(
        "jd_analysis.complete",
        user_id=str(current_user.id),
        seniority=data.get("seniority"),
        role_type=data.get("role_type"),
        latency_ms=latency_ms,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

    return JdAnalysisResponse(
        skills_required=data.get("skills_required", [])[:10],
        skills_nice_to_have=data.get("skills_nice_to_have", [])[:8],
        seniority=data.get("seniority", "unknown"),
        role_type=data.get("role_type", "other"),
        suggested_session_type=data.get("suggested_session_type", "behavioral"),
        suggested_company=suggested_company,
        focus_areas=focus_areas,
        coaching_note=data.get("coaching_note", ""),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionDetail:
    """Fetch full session detail including transcript."""
    session = await _get_owned_session(db, session_id, current_user.id)
    return SessionDetail.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def end_session(
    session_id: uuid.UUID,
    body: SessionEnd,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionResponse:
    """Mark a session as completed or abandoned."""
    session = await _get_owned_session(db, session_id, current_user.id)
    assert session is not None  # _get_owned_session raises 404 when None

    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Session is already {session.status}",
        )

    session.status = body.status
    session.ended_at = datetime.now(tz=UTC)
    await db.commit()
    await db.refresh(session)

    logger.info("sessions.ended", session_id=str(session_id), status=body.status)
    return SessionResponse.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a session permanently. Only non-active sessions can be deleted."""
    session = await _get_owned_session(db, session_id, current_user.id)
    assert session is not None  # _get_owned_session raises 404 when None

    if session.status == SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an active session — end it first",
        )

    await db.delete(session)
    await db.commit()
    logger.info("sessions.deleted", session_id=str(session_id))


# ── GET /sessions/{id}/metrics ─────────────────────────────────────────────────


@router.get("/{session_id}/metrics")
async def get_session_metrics(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Return aggregated latency metrics for a session (STT/LLM/TTS/E2E p50/p95)."""
    await _get_owned_session(db, session_id, current_user.id)

    result = await db.execute(
        select(_SessionMetrics).where(_SessionMetrics.session_id == session_id)
    )
    rows = result.scalars().all()

    def _pct(vals: list[int], p: int) -> int | None:
        if not vals:
            return None
        s = sorted(vals)
        return s[min(int(len(s) * p / 100), len(s) - 1)]

    def _avg(vals: list[int]) -> int | None:
        return round(sum(vals) / len(vals)) if vals else None

    e2e = [r.e2e_latency_ms for r in rows if r.e2e_latency_ms is not None]
    stt = [r.stt_latency_ms for r in rows if r.stt_latency_ms is not None]
    llm = [r.llm_ttft_ms for r in rows if r.llm_ttft_ms is not None]
    tts = [r.tts_latency_ms for r in rows if r.tts_latency_ms is not None]

    return {
        "turns": len(rows),
        "e2e_p50_ms": _pct(e2e, 50),
        "e2e_p95_ms": _pct(e2e, 95),
        "e2e_avg_ms": _avg(e2e),
        "stt_avg_ms": _avg(stt),
        "llm_avg_ms": _avg(llm),
        "tts_avg_ms": _avg(tts),
    }


# -- GET /sessions/{id}/report


@router.get("/{session_id}/report")
async def get_session_report(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate and stream a PDF coaching report for a completed session.

    Returns the PDF as application/pdf. Result is cached 24h in Redis.
    """
    from fastapi.responses import Response as FResponse

    from app.services.report.generator import download_report_pdf, generate_session_pdf

    try:
        file_id = await generate_session_pdf(
            session_id=session_id,
            user_id=current_user.id,
            api_key=settings.anthropic_api_key,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    pdf_bytes = await download_report_pdf(file_id, settings.anthropic_api_key)
    return FResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="report-{session_id}.pdf"'},
    )


# ── WebSocket voice endpoint ───────────────────────────────────────────────────


@router.websocket("/{session_id}/voice")
async def voice_websocket(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str = Query(..., description="JWT access token"),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Real-time voice pipeline WebSocket.

    Auth: pass access token as ?token=<jwt> query param.
    The pipeline runs until the client sends {type: "end_audio"} or disconnects.

    Latency target: p50 < 800ms E2E (logged to session_metrics every turn).
    """
    await websocket.accept()

    # ── Authenticate via token query param ─────────────────────────────────────
    user = await _authenticate_ws(token, db)
    if user is None:
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close(code=1008)
        return

    # ── Load session ───────────────────────────────────────────────────────────
    session = await _get_owned_session(db, session_id, user.id, raise_http=False)
    if session is None or session.status != SessionStatus.ACTIVE:
        await websocket.send_json({"type": "error", "message": "Session not found or not active"})
        await websocket.close(code=1008)
        return

    logger.info(
        "voice_ws.connected",
        session_id=str(session_id),
        user_id=str(user.id),
        profile=session.quality_profile,
    )

    # ── Build pipeline ─────────────────────────────────────────────────────────
    try:
        byok_keys = decrypt_byok_keys(user.byok_keys, settings.secret_key)
        profile_settings = (user.profile or {}).get("app_settings") or {}
        openai_model = profile_settings.get("openai_model", "gpt-4o")
        providers = ProviderFactory.create(
            session.quality_profile,
            settings,
            voice_id=session.voice_id,
            byok_keys=byok_keys or None,
            openai_model=openai_model,
        )

        # Fetch company-specific questions to inject into the session prompt
        company_questions: list[str] = []
        company = getattr(session, "company", None)
        if company:
            q_result = await db.execute(
                select(Question)
                .where(Question.company == company)
                .where(Question.type == session.type)
                .order_by(Question.times_used)
                .limit(5)
            )
            company_questions = [q.text for q in q_result.scalars().all()]

        # Build candidate context from resume + cross-session memory
        resume_data = ((user.profile or {}).get("resume")) or {}
        candidate_context = build_candidate_context_block(resume_data) or None

        memory_block = await load_memory_context(
            db=db,
            user_id=user.id,
            api_key=settings.anthropic_api_key or None,
        )
        if memory_block:
            candidate_context = (candidate_context or "") + "\n\n" + memory_block

        pipeline = VoicePipeline(
            providers=providers,
            db=db,
            session=session,
            user_id=user.id,
            company_questions=company_questions,
            candidate_context=candidate_context,
            duration_limit_minutes=session.duration_limit_minutes,
        )
        await pipeline.run(websocket)
    except WebSocketDisconnect:
        logger.info("voice_ws.client_disconnected", session_id=str(session_id))
    except Exception as exc:
        logger.error("voice_ws.pipeline_error", error=str(exc), session_id=str(session_id))
        try:
            await websocket.send_json({"type": "error", "message": "Internal pipeline error"})
        except Exception:
            pass
    finally:
        logger.info("voice_ws.closed", session_id=str(session_id))


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _authenticate_ws(token: str, db: AsyncSession) -> User | None:
    """Decode WS auth token and return the User, or None if invalid."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    return result.scalar_one_or_none()


async def _get_owned_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    raise_http: bool = True,
) -> InterviewSession | None:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None and raise_http:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session
