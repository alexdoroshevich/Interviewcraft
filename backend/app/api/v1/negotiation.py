"""Negotiation Simulator API.

POST /api/v1/negotiation/start     — create negotiation session with recruiter context
GET  /api/v1/negotiation/history   — list past negotiation sessions
GET  /api/v1/negotiation/{id}/analysis — detailed analysis + pattern detection

Architecture:
- Negotiation sessions are regular InterviewSession rows (type="negotiation").
- Recruiter persona + offer context stored in session.lint_results["negotiation_context"].
- Negotiation scoring uses the existing rubric (weak_anchor + early_concession rules)
  plus a post-session Haiku call for money_left_on_table estimation.
- Pattern detection runs across the last 3 negotiation sessions.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any, cast

import structlog
from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.interview_session import InterviewSession, SessionStatus, SessionType
from app.schemas.negotiation import (
    NegotiationAnalysisResponse,
    NegotiationHistoryItem,
    NegotiationScores,
    NegotiationStartRequest,
    NegotiationStartResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.usage import log_usage
from app.services.voice.costs import calc_anthropic_cost

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/negotiation", tags=["negotiation"])

_HAIKU = "claude-haiku-4-5-20251001"

# Hidden max budget: 15% above the stated offer
_HIDDEN_MAX_MULTIPLIER = 1.15

# ── Pattern detection prompt lines ────────────────────────────────────────────

_PATTERNS = [
    "You consistently concede on equity before exhausting base salary options.",
    "You improve on base anchoring but undervalue total compensation.",
    "You tend to accept the first counter-offer without probing for flexibility.",
    "Your anchoring improves each round — keep building on this.",
    "You often provide justification when the interviewer hasn't asked — this weakens your position.",
]


# ── POST /api/v1/negotiation/start ───────────────────────────────────────────


@router.post(
    "/start",
    response_model=NegotiationStartResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_negotiation(
    body: NegotiationStartRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NegotiationStartResponse:
    """Create a new negotiation practice session.

    Stores recruiter persona context in lint_results["negotiation_context"].
    The voice pipeline will use this context when building the system prompt.
    """
    hidden_max = int(body.offer_amount * _HIDDEN_MAX_MULTIPLIER)

    negotiation_context = {
        "company": body.company,
        "role": body.role,
        "level": body.level,
        "offer_amount": body.offer_amount,
        "market_rate": body.market_rate,
        "hidden_max": hidden_max,
        "lowball": int(body.offer_amount * 0.9),  # 10% below their offer
    }

    session = InterviewSession(
        user_id=current_user.id,
        type=SessionType.NEGOTIATION,
        quality_profile=body.quality_profile,
        lint_results={"negotiation_context": negotiation_context},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(
        "negotiation.session_started",
        session_id=str(session.id),
        user_id=str(current_user.id),
        company=body.company,
        offer_amount=body.offer_amount,
        hidden_max=hidden_max,
    )

    return NegotiationStartResponse(
        session_id=session.id,
        company=body.company,
        role=body.role,
        level=body.level,
        offer_amount=body.offer_amount,
        market_rate=body.market_rate,
    )


# ── GET /api/v1/negotiation/history ──────────────────────────────────────────


@router.get("/history", response_model=list[NegotiationHistoryItem])
async def get_negotiation_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[NegotiationHistoryItem]:
    """List all negotiation sessions for the current user."""
    result = await db.execute(
        select(InterviewSession)
        .where(
            InterviewSession.user_id == current_user.id,
            InterviewSession.type == SessionType.NEGOTIATION,
        )
        .order_by(InterviewSession.created_at.desc())
        .limit(20)
    )
    sessions = list(result.scalars().all())

    items = []
    for s in sessions:
        ctx = (s.lint_results or {}).get("negotiation_context", {})
        analysis = (s.lint_results or {}).get("negotiation_analysis", {})

        items.append(
            NegotiationHistoryItem(
                session_id=s.id,
                company=ctx.get("company", "Unknown"),
                role=ctx.get("role", "Unknown"),
                level=ctx.get("level", "Unknown"),
                offer_amount=ctx.get("offer_amount", 0),
                overall_score=analysis.get("overall_score", 0),
                money_left_on_table=analysis.get("money_left_on_table", 0),
                created_at=s.created_at,
                status=s.status,
            )
        )
    return items


# ── GET /api/v1/negotiation/{id}/analysis ────────────────────────────────────


@router.get("/{session_id}/analysis", response_model=NegotiationAnalysisResponse)
async def get_negotiation_analysis(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> NegotiationAnalysisResponse:
    """Get detailed negotiation analysis for a completed session.

    If the session hasn't been scored yet, triggers scoring now.
    Pattern detection runs across last 3 negotiation sessions.
    """
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
            InterviewSession.type == SessionType.NEGOTIATION,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Negotiation session not found",
        )

    ctx = (session.lint_results or {}).get("negotiation_context", {})
    existing_analysis = (session.lint_results or {}).get("negotiation_analysis")

    if existing_analysis:
        neg_scores = NegotiationScores(**existing_analysis["negotiation_scores"])
    elif session.status == SessionStatus.COMPLETED and session.transcript:
        # Run analysis
        analysis_data = await _analyze_negotiation(
            db=db,
            session=session,
            ctx=ctx,
            user_id=current_user.id,
        )
        existing_analysis = analysis_data
        neg_scores = NegotiationScores(**analysis_data["negotiation_scores"])
    else:
        # Not completed or no transcript yet
        neg_scores = NegotiationScores(
            anchoring=0,
            value_articulation=0,
            counter_strategy=0,
            emotional_control=0,
            money_left_on_table=0,
        )
        existing_analysis = {"overall_score": 0, "pattern_detected": None, "improvement_notes": []}

    # Detect cross-session patterns
    pattern = await _detect_pattern(db, current_user.id, session_id)

    return NegotiationAnalysisResponse(
        session_id=session.id,
        company=ctx.get("company", "Unknown"),
        role=ctx.get("role", "Unknown"),
        level=ctx.get("level", "Unknown"),
        offer_amount=ctx.get("offer_amount", 0),
        market_rate=ctx.get("market_rate", 0),
        hidden_max=ctx.get("hidden_max", 0),
        overall_score=existing_analysis.get("overall_score", 0),
        negotiation_scores=neg_scores,
        pattern_detected=pattern,
        rounds_completed=1,
        improvement_notes=existing_analysis.get("improvement_notes", []),
    )


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _analyze_negotiation(
    db: AsyncSession,
    session: InterviewSession,
    ctx: dict[str, Any],
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Use Haiku to analyze a negotiation transcript and score it."""
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    transcript_text = "\n".join(
        f"{'RECRUITER' if t.get('role') == 'assistant' else 'CANDIDATE'}: {t.get('content', '')}"
        for t in (session.transcript or [])[:40]
    )

    schema: dict[str, Any] = {
        "type": "object",
        "required": [
            "anchoring",
            "value_articulation",
            "counter_strategy",
            "emotional_control",
            "money_left_on_table",
            "overall_score",
            "improvement_notes",
        ],
        "properties": {
            "anchoring": {"type": "integer", "minimum": 0, "maximum": 100},
            "value_articulation": {"type": "integer", "minimum": 0, "maximum": 100},
            "counter_strategy": {"type": "integer", "minimum": 0, "maximum": 100},
            "emotional_control": {"type": "integer", "minimum": 0, "maximum": 100},
            "money_left_on_table": {"type": "integer", "minimum": 0},
            "overall_score": {"type": "integer", "minimum": 0, "maximum": 100},
            "improvement_notes": {"type": "array", "items": {"type": "string"}},
        },
    }

    prompt = f"""Analyze this salary negotiation transcript and score the candidate.

Context:
- Company: {ctx.get("company")} | Role: {ctx.get("role")} | Level: {ctx.get("level")}
- Their offer: ${ctx.get("offer_amount"):,}
- Candidate's market rate: ${ctx.get("market_rate"):,}
- Hidden max budget (for scoring): ${ctx.get("hidden_max"):,}

=== TRANSCRIPT ===
{transcript_text}

Score the candidate (0-100) on:
1. anchoring: Did they set a strong first anchor? (High if they named a number 15%+ above market)
2. value_articulation: Did they justify their market value with specifics?
3. counter_strategy: Did they push back on objections without immediate concession?
4. emotional_control: Did they stay calm, avoid over-justifying, not concede under pressure?
5. money_left_on_table: Estimated $ not captured vs hidden max ({ctx.get("hidden_max"):,})
6. overall_score: Weighted average (anchoring 30%, value 20%, counter 30%, control 20%)
7. improvement_notes: 2-3 specific, actionable improvement notes

Be realistic. Most candidates leave money on the table.
"""

    response = await client.messages.create(
        model=_HAIKU,
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
        tools=[
            {
                "name": "score_negotiation",
                "description": "Score negotiation",
                "input_schema": schema,
            }
        ],
        tool_choice={"type": "tool", "name": "score_negotiation"},
    )

    usage = response.usage
    cost = calc_anthropic_cost(
        model=_HAIKU,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_tokens=0,
    )
    await log_usage(
        db=db,
        session_id=session.id,
        user_id=user_id,
        provider="anthropic",
        operation="negotiation_scoring",
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_tokens=0,
        cost_usd=cost,
        latency_ms=0,
        quality_profile=session.quality_profile,
        cached=False,
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "score_negotiation":
            result = cast(dict[str, Any], block.input)
            analysis = {
                "negotiation_scores": {
                    "anchoring": result["anchoring"],
                    "value_articulation": result["value_articulation"],
                    "counter_strategy": result["counter_strategy"],
                    "emotional_control": result["emotional_control"],
                    "money_left_on_table": result["money_left_on_table"],
                },
                "overall_score": result["overall_score"],
                "improvement_notes": result["improvement_notes"],
                "money_left_on_table": result["money_left_on_table"],
                "pattern_detected": None,
            }
            # Persist
            session.lint_results = {
                **(session.lint_results or {}),
                "negotiation_analysis": analysis,
            }
            await db.commit()
            return analysis

    raise ValueError("No tool_use block from negotiation analysis")


async def _detect_pattern(
    db: AsyncSession,
    user_id: uuid.UUID,
    current_session_id: uuid.UUID,
) -> str | None:
    """Detect cross-session patterns across last 3 negotiation sessions."""
    result = await db.execute(
        select(InterviewSession)
        .where(
            InterviewSession.user_id == user_id,
            InterviewSession.type == SessionType.NEGOTIATION,
            InterviewSession.status == SessionStatus.COMPLETED,
        )
        .order_by(InterviewSession.created_at.desc())
        .limit(3)
    )
    sessions = list(result.scalars().all())

    if len(sessions) < 2:
        return None  # need at least 2 rounds to detect a pattern

    # Look at negotiation_analysis across sessions
    analyses = [(s.lint_results or {}).get("negotiation_analysis", {}) for s in sessions]

    # Simple heuristic: if emotional_control consistently < 60, flag it
    controls = [a.get("negotiation_scores", {}).get("emotional_control", 0) for a in analyses]
    if all(c < 60 for c in controls if c > 0):
        return "Pattern: You consistently struggle with emotional control under pressure. Practice staying calm when they say 'this is our final offer'."

    # If anchoring improved but counter_strategy still low
    anchoring_scores = [a.get("negotiation_scores", {}).get("anchoring", 0) for a in analyses]
    counter_scores = [a.get("negotiation_scores", {}).get("counter_strategy", 0) for a in analyses]
    if len(anchoring_scores) >= 2 and anchoring_scores[0] > anchoring_scores[-1]:
        if counter_scores and counter_scores[0] < 55:
            return "Pattern: Your anchoring is improving but counter-strategy needs work. Next time: when they push back, ask 'What's driving that constraint?' before moving your position."

    # If money left on table is consistently high
    money_left = [a.get("money_left_on_table", 0) for a in analyses]
    if money_left and all(m > 10000 for m in money_left if m > 0):
        return f"Pattern: You've left ${min(money_left):,}-${max(money_left):,} on the table across {len(sessions)} sessions. Focus on probing for flexibility in equity and signing bonus."

    return None
