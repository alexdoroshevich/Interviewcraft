"""Scoring endpoints.

POST /api/v1/sessions/{id}/score  — trigger scoring for a completed session
GET  /api/v1/sessions/{id}/scores — retrieve all segment scores for a session

Architecture:
- Scoring is triggered by the client after a session ends (not automatically,
  so the UI can show a "Scoring..." loading state).
- Each Q&A exchange in session.transcript is scored as a separate segment.
- Results stored in segment_scores table + summary stored in session.lint_results.
- Prompt caching means the second+ call per session is 90% cheaper.
"""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.interview_session import InterviewSession, SessionStatus
from app.models.segment_score import SegmentScore
from app.models.story import Story
from app.schemas.scoring import (
    DeliveryAnalysisResponse,
    ScoringRequest,
    ScoringStatusResponse,
    SegmentScoreResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.delivery.analyzer import analyze_delivery
from app.services.memory.builder import build_memory
from app.services.memory.skill_graph import skill_graph_service
from app.services.scoring.scorer import Scorer, ScoringResult

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["scoring"])


# ── POST /api/v1/sessions/{id}/score ──────────────────────────────────────────


@router.post(
    "/api/v1/sessions/{session_id}/score",
    response_model=ScoringStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def score_session(
    session_id: uuid.UUID,
    body: ScoringRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ScoringStatusResponse:
    """Score all Q&A segments in a completed session.

    - Triggers one Anthropic call per segment (score + diff + memory hints).
    - Rubric prefix is prompt-cached → 90% cheaper after first call.
    - Idempotent: returns existing scores unless force_rescore=True.
    """
    session = await _get_owned_session(db, session_id, current_user.id)

    if session.status == SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session is still active — end it before scoring.",
        )

    # Idempotency: skip if already scored (unless forced)
    # Check for scoring-specific key, not just any lint_results (negotiation pre-populates context)
    if (
        session.lint_results
        and session.lint_results.get("segments_scored")
        and not body.force_rescore
    ):
        existing = await _get_segment_scores(db, session_id)
        # Still run skill graph update in case it was missed (e.g. server restarted after scoring)
        if not session.lint_results.get("skill_graph_updated"):
            for row in existing:
                try:
                    await skill_graph_service.update_from_scoring_result(
                        db=db,
                        user_id=current_user.id,
                        session_id=session_id,
                        segment_index=row.segment_index,
                        overall_score=row.overall_score,
                        rules_triggered=row.rules_triggered or [],
                        memory_hints={},
                        question_type=session.type,
                    )
                except Exception as exc:
                    logger.warning("scoring.skill_graph_backfill_failed", error=str(exc))
            updated = dict(session.lint_results)
            updated["skill_graph_updated"] = True
            session.lint_results = updated
            await db.commit()
        return _build_status_response(session_id, existing)

    # Extract Q&A segments from transcript
    segments = _extract_qa_segments(session.transcript)
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No Q&A segments found in transcript.",
        )

    scorer = Scorer(
        api_key=settings.anthropic_api_key,
        quality_profile=session.quality_profile,
    )

    scored_rows: list[SegmentScore] = []
    total_cost = Decimal("0")
    total_cached_tokens = 0

    # Score all segments in parallel for ~3x speedup
    async def _score_one(
        idx: int, question: str, answer_turns: list[dict]
    ) -> tuple[int, str, list[dict], ScoringResult]:
        return (
            idx,
            question,
            answer_turns,
            await scorer.score_segment(
                session_id=session_id,
                segment_index=idx,
                question=question,
                answer_transcript=answer_turns,
                question_type=session.type,
                target_level="L5",
                db=db,
                user_id=current_user.id,
            ),
        )

    tasks = [_score_one(idx, q, a) for idx, (q, a) in enumerate(segments)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for res in results:
        if isinstance(res, Exception):
            logger.error("scoring.segment_failed", session_id=str(session_id), error=str(res))
            continue

        idx, question, answer_turns, result = res  # type: ignore[misc]
        row = SegmentScore(
            session_id=session_id,
            segment_index=idx,
            question_text=question,
            answer_text=_turns_to_text(answer_turns),
            overall_score=result.overall_score,
            confidence=result.confidence,
            category_scores=result.categories,
            rules_triggered=result.rules_triggered,
            level_assessment=result.level_assessment,
            diff_versions=result.diff_versions,
        )
        db.add(row)
        scored_rows.append(row)

        seg_cost = _calc_segment_cost(result)
        total_cost += seg_cost
        total_cached_tokens += result.cached_tokens

    # ── Skill graph update + story auto-detection ─────────────────────────────
    # For each successfully scored segment, apply skill signals to the user's
    # skill graph and auto-save stories when the LLM detected a compelling one.
    # These run sequentially (safe — no shared-session concurrency issue).
    _existing_story_titles = set()
    for res in results:
        if isinstance(res, Exception):
            continue
        idx, question, answer_turns, result = res  # type: ignore[misc]

        # Update skill graph with rules_triggered + memory_hints.skill_signals
        try:
            await skill_graph_service.update_from_scoring_result(
                db=db,
                user_id=current_user.id,
                session_id=session_id,
                segment_index=idx,
                overall_score=result.overall_score,
                rules_triggered=result.rules_triggered,
                memory_hints=result.memory_hints,
                question_type=session.type,
            )
        except Exception as exc:
            logger.warning(
                "scoring.skill_graph_update_failed",
                session_id=str(session_id),
                segment_index=idx,
                error=str(exc),
            )

        # Auto-detect stories — create a Story row if one was found and not yet saved
        hints = result.memory_hints or {}
        if hints.get("story_detected") and hints.get("story_title"):
            title = (hints["story_title"] or "").strip()
            if not title or title in _existing_story_titles:
                continue
            _existing_story_titles.add(title)
            summary = (hints.get("communication_notes") or "").strip() or (
                f'Auto-detected from "{question[:120]}"'
            )
            story = Story(
                user_id=current_user.id,
                title=title,
                summary=summary,
                competencies=[],
                auto_detected=True,
                source_session_id=session_id,
            )
            db.add(story)
            logger.info(
                "scoring.story_auto_detected",
                session_id=str(session_id),
                title=title,
            )

    # Persist lint_results summary on the session (merge, don't overwrite)
    if scored_rows:
        existing_lint = session.lint_results or {}
        existing_lint.update(_build_lint_summary(scored_rows))
        existing_lint["skill_graph_updated"] = True
        session.lint_results = existing_lint
        session.total_cost_usd = session.total_cost_usd + total_cost

    await db.commit()
    for row in scored_rows:
        await db.refresh(row)

    logger.info(
        "scoring.session_scored",
        session_id=str(session_id),
        segments=len(scored_rows),
        total_cost_usd=str(total_cost),
        cache_hit_tokens=total_cached_tokens,
    )

    # Fire memory extraction in the background — non-blocking, won't delay the response.
    asyncio.create_task(
        build_memory(
            db=db,
            session=session,
            user_id=current_user.id,
            api_key=settings.anthropic_api_key,
        )
    )

    return _build_status_response(session_id, scored_rows, total_cost, total_cached_tokens)


# ── GET /api/v1/sessions/{id}/scores ──────────────────────────────────────────


@router.get(
    "/api/v1/sessions/{session_id}/scores",
    response_model=list[SegmentScoreResponse],
)
async def get_scores(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SegmentScoreResponse]:
    """Return all scored segments for a session."""
    await _get_owned_session(db, session_id, current_user.id)  # ownership check
    rows = await _get_segment_scores(db, session_id)
    return [SegmentScoreResponse.model_validate(r) for r in rows]


# ── POST /api/v1/sessions/{id}/scores/{segment}/play-ideal ────────────────────


@router.post(
    "/api/v1/sessions/{session_id}/scores/{segment_index}/play-ideal",
    status_code=status.HTTP_200_OK,
)
async def play_ideal_answer(
    session_id: uuid.UUID,
    segment_index: int,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Generate TTS audio for the ideal answer version of a scored segment.

    Returns base64-encoded MP3 audio for browser playback.
    Uses Deepgram Aura-1 (budget TTS) to keep costs low.
    """
    await _get_owned_session(db, session_id, current_user.id)

    # Get the segment score
    result = await db.execute(
        select(SegmentScore).where(
            SegmentScore.session_id == session_id,
            SegmentScore.segment_index == segment_index,
        )
    )
    segment = result.scalar_one_or_none()
    if segment is None:
        raise HTTPException(status_code=404, detail="Segment score not found")

    diff_versions = segment.diff_versions
    if not diff_versions or "ideal" not in diff_versions:
        raise HTTPException(status_code=404, detail="No ideal answer version available")

    ideal_text = diff_versions["ideal"].get("text", "")
    if not ideal_text:
        raise HTTPException(status_code=422, detail="Ideal answer text is empty")

    # Generate TTS audio via Deepgram Aura-1 (budget, fast)
    import base64

    import httpx

    audio_chunks: list[bytes] = []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.deepgram.com/v1/speak",
                headers={
                    "Authorization": f"Token {settings.deepgram_api_key}",
                    "Content-Type": "application/json",
                },
                params={"model": "aura-asteria-en", "encoding": "mp3"},
                json={"text": ideal_text[:2000]},  # Cap at 2000 chars
            )
            response.raise_for_status()
            audio_chunks.append(response.content)
    except Exception as exc:
        logger.error("scoring.ideal_tts_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to generate audio")

    audio_bytes = b"".join(audio_chunks)
    audio_b64 = base64.b64encode(audio_bytes).decode()

    logger.info(
        "scoring.ideal_tts_generated",
        session_id=str(session_id),
        segment_index=segment_index,
        chars=len(ideal_text),
        audio_bytes=len(audio_bytes),
    )

    return {
        "audio_data": audio_b64,
        "format": "mp3",
        "text": ideal_text,
        "characters": len(ideal_text),
    }


# ── GET /api/v1/sessions/{id}/delivery ────────────────────────────────────────


@router.get(
    "/api/v1/sessions/{session_id}/delivery",
    response_model=DeliveryAnalysisResponse,
)
async def get_delivery_analysis(
    session_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DeliveryAnalysisResponse:
    """Return voice delivery analysis for a session.

    Metrics: filler words, WPM, hesitation gaps, delivery score.
    Uses word-level timestamps when available (14d TTL), falls back to turn-level analysis.
    Results are cached in session.lint_results["delivery"] after first computation.
    """
    session = await _get_owned_session(db, session_id, current_user.id)

    # Return cached result if available
    cached = (session.lint_results or {}).get("delivery")
    if cached:
        return DeliveryAnalysisResponse(**cached)

    transcript = session.transcript or []
    analysis = await analyze_delivery(
        session_id=session_id,
        transcript=transcript,
        db=db,
    )

    # Cache result in lint_results so we don't recompute after transcript_words expire
    existing_lint = dict(session.lint_results) if session.lint_results else {}
    existing_lint["delivery"] = {
        "total_words": analysis.total_words,
        "duration_seconds": analysis.duration_seconds,
        "wpm": analysis.wpm,
        "filler_count": analysis.filler_count,
        "filler_rate": analysis.filler_rate,
        "fillers_by_type": analysis.fillers_by_type,
        "top_filler": analysis.top_filler,
        "hesitation_gaps": analysis.hesitation_gaps,
        "long_pause_count": analysis.long_pause_count,
        "has_word_timestamps": analysis.has_word_timestamps,
        "delivery_score": analysis.delivery_score,
        "delivery_grade": analysis.delivery_grade,
        "coaching_tips": analysis.coaching_tips,
    }
    session.lint_results = existing_lint
    await db.commit()

    logger.info(
        "delivery.analyzed",
        session_id=str(session_id),
        wpm=analysis.wpm,
        fillers=analysis.filler_count,
        score=analysis.delivery_score,
        has_word_timestamps=analysis.has_word_timestamps,
    )

    return DeliveryAnalysisResponse(**existing_lint["delivery"])


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_owned_session(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> InterviewSession:
    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


async def _get_segment_scores(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> list[SegmentScore]:
    result = await db.execute(
        select(SegmentScore)
        .where(SegmentScore.session_id == session_id)
        .order_by(SegmentScore.segment_index)
    )
    return list(result.scalars().all())


_MIN_ANSWER_WORDS = 15  # Skip greetings, short acknowledgments — not worth scoring


def _extract_qa_segments(
    transcript: list[dict],
) -> list[tuple[str, list[dict]]]:
    """Split transcript into (question, answer_turns) pairs.

    The transcript is a list of {role, content, ts_ms} dicts.
    We pair each assistant question with the user turns that follow it,
    up to the next assistant turn.

    Segments where the user's total answer is < _MIN_ANSWER_WORDS words are
    skipped — this filters out greeting exchanges like "Hi, I'm ready to start."
    """
    segments: list[tuple[str, list[dict]]] = []
    current_question: str | None = None
    current_answer: list[dict] = []

    for turn in transcript:
        role = turn.get("role", "")
        content = turn.get("content", "")

        if role == "assistant":
            # Save previous segment if we have a substantive answer
            if current_question and current_answer:
                answer_words = sum(
                    len(t.get("content", "").split())
                    for t in current_answer
                    if t.get("role") == "user"
                )
                if answer_words >= _MIN_ANSWER_WORDS:
                    segments.append((current_question, list(current_answer)))
            current_question = content
            current_answer = []
        elif role == "user" and current_question:
            current_answer.append(turn)

    # Capture last segment
    if current_question and current_answer:
        answer_words = sum(
            len(t.get("content", "").split()) for t in current_answer if t.get("role") == "user"
        )
        if answer_words >= _MIN_ANSWER_WORDS:
            segments.append((current_question, list(current_answer)))

    return segments


def _turns_to_text(turns: list[dict]) -> str:
    return " ".join(t.get("content", "") for t in turns if t.get("role") == "user")


def _calc_segment_cost(result: object) -> Decimal:
    from app.services.voice.costs import calc_anthropic_cost

    model = getattr(result, "model", "claude-haiku-4-5")
    return calc_anthropic_cost(
        model=model,
        input_tokens=getattr(result, "input_tokens", 0),
        output_tokens=getattr(result, "output_tokens", 0),
        cached_tokens=getattr(result, "cached_tokens", 0),
    )


def _build_lint_summary(rows: list[SegmentScore]) -> dict:
    """Build the session.lint_results summary from scored segments."""
    return {
        "segments_scored": len(rows),
        "average_score": round(sum(r.overall_score for r in rows) / len(rows)),
        "scores": [
            {
                "segment_index": r.segment_index,
                "overall_score": r.overall_score,
                "confidence": r.confidence,
                "rules_count": len(r.rules_triggered),
                "level_assessment": r.level_assessment,
            }
            for r in rows
        ],
    }


def _build_status_response(
    session_id: uuid.UUID,
    rows: list[SegmentScore],
    total_cost: Decimal = Decimal("0"),
    total_cached_tokens: int = 0,
) -> ScoringStatusResponse:
    return ScoringStatusResponse(
        session_id=session_id,
        segments_scored=len(rows),
        total_cost_usd=float(total_cost),
        cache_hit_tokens=total_cached_tokens,
        scores=[SegmentScoreResponse.model_validate(r) for r in rows],
    )
