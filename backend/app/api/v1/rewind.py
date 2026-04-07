"""Rewind API — re-ask a segment question, re-score, return delta.

POST /api/v1/sessions/{id}/rewind
    Body: {segment_id: uuid}
    Returns: question + hint + original score context

POST /api/v1/sessions/{id}/rewind/{segment_id}/score
    Body: {answer_text: str}
    Returns: delta score, categories delta, explanation

Architecture (ADR-004):
- Segment = one question-answer pair (not arbitrary timestamps).
- Rewind re-asks the SAME question with a "this time, fix X" hint.
- Re-scoring uses SAME Scorer class with SAME rubric → consistency.
- delta = new_score - original_score.
- Updates segment_scores.rewind_count and best_rewind_score.
- Updates skill graph with new result.
"""

from __future__ import annotations

import typing
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.interview_session import InterviewSession
from app.models.segment_score import SegmentScore
from app.schemas.skills import (
    CategoryDelta,
    RewindScoreRequest,
    RewindScoreResponse,
    RewindStartResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.memory.skill_graph import skill_graph_service
from app.services.scoring.scorer import Scorer

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["rewind"])


# ── POST /api/v1/sessions/{id}/rewind ────────────────────────────────────────


class RewindRequest(BaseModel):
    segment_id: uuid.UUID


@router.post(
    "/api/v1/sessions/{session_id}/rewind",
    response_model=RewindStartResponse,
    status_code=status.HTTP_200_OK,
)
async def start_rewind(
    session_id: uuid.UUID,
    body: RewindRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RewindStartResponse:
    """Return context for rewinding a specific segment.

    Looks up the segment score and builds a hint for the user
    about what to fix in their re-answer.
    """
    await _assert_session_owned(db, session_id, current_user.id)
    segment = await _get_segment(db, body.segment_id, session_id)

    # Build hint from rules triggered
    rules_triggered = segment.rules_triggered or []
    rules_to_fix = [r["rule"] for r in rules_triggered[:3]]  # top 3

    hint = _build_rewind_hint(rules_triggered)

    logger.info(
        "rewind.start",
        session_id=str(session_id),
        segment_id=str(segment.id),
        original_score=segment.overall_score,
        rules_to_fix=rules_to_fix,
    )

    return RewindStartResponse(
        segment_id=segment.id,
        question=segment.question_text,
        original_score=segment.overall_score,
        original_answer_text=segment.answer_text,
        hint=hint,
        rules_to_fix=rules_to_fix,
    )


# ── POST /api/v1/sessions/{id}/rewind/{segment_id}/score ─────────────────────


@router.post(
    "/api/v1/sessions/{session_id}/rewind/{segment_id}/score",
    response_model=RewindScoreResponse,
    status_code=status.HTTP_200_OK,
)
async def score_rewind(
    session_id: uuid.UUID,
    segment_id: uuid.UUID,
    body: RewindScoreRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RewindScoreResponse:
    """Re-score a rewind answer and return the delta.

    Steps:
    1. Load original segment and session.
    2. Score the new answer_text using same rubric.
    3. Compute delta and category changes.
    4. Update segment_score.rewind_count + best_rewind_score.
    5. Update skill graph.
    """
    session = await _assert_session_owned(db, session_id, current_user.id)
    segment = await _get_segment(db, segment_id, session_id)

    if not body.answer_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="answer_text cannot be empty",
        )

    # Build a synthetic transcript for re-scoring (text-based, no voice timestamps)
    rewind_transcript = [
        {"role": "assistant", "content": segment.question_text, "ts_ms": 0},
        {"role": "user", "content": body.answer_text, "ts_ms": 1000},
    ]

    scorer = Scorer(
        api_key=settings.anthropic_api_key,
        quality_profile=session.quality_profile,
    )

    try:
        result = await scorer.score_segment(
            session_id=session_id,
            segment_index=segment.segment_index,
            question=segment.question_text,
            answer_transcript=rewind_transcript,
            question_type=session.type,
            target_level="L5",
            db=db,
            user_id=current_user.id,
        )
    except RuntimeError as exc:
        logger.error(
            "rewind.scoring_failed",
            segment_id=str(segment_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Scoring service temporarily unavailable. Please try again.",
        ) from exc

    # Compute delta
    original_score = segment.overall_score
    new_score = result.overall_score
    delta = new_score - original_score

    # Category deltas
    orig_cats = segment.category_scores or {}
    new_cats = result.categories
    cat_delta = CategoryDelta(
        structure=new_cats.get("structure", 0) - orig_cats.get("structure", 0),
        depth=new_cats.get("depth", 0) - orig_cats.get("depth", 0),
        communication=new_cats.get("communication", 0) - orig_cats.get("communication", 0),
        seniority_signal=(
            new_cats.get("seniority_signal", 0) - orig_cats.get("seniority_signal", 0)
        ),
    )

    # Which rules were fixed vs newly triggered?
    original_rules = {r["rule"] for r in (segment.rules_triggered or [])}
    new_rules = {r["rule"] for r in result.rules_triggered}
    rules_fixed = list(original_rules - new_rules)
    rules_new = list(new_rules - original_rules)

    reason = _build_delta_reason(delta, rules_fixed, rules_new, cat_delta)

    # Update segment tracking
    segment.rewind_count = (segment.rewind_count or 0) + 1
    segment.best_rewind_score = max(
        segment.best_rewind_score or 0,
        new_score,
    )

    # Update skill graph
    await skill_graph_service.update_from_scoring_result(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        segment_index=segment.segment_index,
        overall_score=new_score,
        rules_triggered=result.rules_triggered,
        memory_hints=result.memory_hints,
        question_type=session.type,
    )

    await db.commit()

    logger.info(
        "rewind.scored",
        session_id=str(session_id),
        segment_id=str(segment_id),
        original_score=original_score,
        new_score=new_score,
        delta=delta,
        rules_fixed=rules_fixed,
        rewind_count=segment.rewind_count,
    )

    return RewindScoreResponse(
        segment_id=segment.id,
        original_score=original_score,
        new_score=new_score,
        delta=delta,
        categories_delta=cat_delta,
        rules_fixed=rules_fixed,
        rules_new=rules_new,
        reason=reason,
        rewind_count=segment.rewind_count,
        best_rewind_score=segment.best_rewind_score,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _assert_session_owned(
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


async def _get_segment(
    db: AsyncSession,
    segment_id: uuid.UUID,
    session_id: uuid.UUID,
) -> SegmentScore:
    result = await db.execute(
        select(SegmentScore).where(
            SegmentScore.id == segment_id,
            SegmentScore.session_id == session_id,
        )
    )
    seg = result.scalar_one_or_none()
    if seg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segment not found in this session",
        )
    return seg


def _build_rewind_hint(rules_triggered: list[dict[str, typing.Any]]) -> str:
    """Build a concise hint about what to fix in the rewind answer."""
    if not rules_triggered:
        return (
            "Good attempt! Try to sharpen your answer further — add more specific "
            "metrics and think about what the interviewer was really probing for."
        )

    fixes = [r.get("fix", "") for r in rules_triggered[:2] if r.get("fix")]
    if not fixes:
        return "This time, focus on making your answer more structured and specific."

    return "This time: " + " Also: ".join(fixes[:2])


def _build_delta_reason(
    delta: int,
    rules_fixed: list[str],
    rules_new: list[str],
    cat_delta: CategoryDelta,
) -> str:
    """Build a human-readable explanation of the score change."""
    if delta == 0:
        return "Score unchanged. The rewind hit the same strengths and weaknesses."

    parts = []

    if delta > 0:
        parts.append(f"Improved by {delta} points.")
    else:
        parts.append(f"Dropped by {abs(delta)} points.")

    if rules_fixed:
        fixed_str = ", ".join(rules_fixed[:3])
        parts.append(f"Fixed: {fixed_str}.")

    if rules_new:
        new_str = ", ".join(rules_new[:2])
        parts.append(f"New issues: {new_str}.")

    # Biggest category change
    cat_items = [
        ("structure", cat_delta.structure),
        ("depth", cat_delta.depth),
        ("communication", cat_delta.communication),
        ("seniority", cat_delta.seniority_signal),
    ]
    biggest = max(cat_items, key=lambda x: abs(x[1]))
    if abs(biggest[1]) >= 5:
        direction = "↑" if biggest[1] > 0 else "↓"
        parts.append(f"{biggest[0].capitalize()}: {direction}{abs(biggest[1])}.")

    return " ".join(parts)
