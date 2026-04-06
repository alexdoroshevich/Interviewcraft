"""Questions API — adaptive question selection from the question bank.

GET  /api/v1/questions/next          — next question for drill plan (skill-based)
GET  /api/v1/questions               — browse question bank (with filters)
POST /api/v1/questions/contribute    — submit a new question for review
GET  /api/v1/questions/contribute    — list current user's submissions
POST /api/v1/questions/{id}/upvote   — upvote a question (one per user)

ChromaDB semantic search deferred to Phase 2.
Current implementation: simple SQL-based skill filtering.
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.question import Question, QuestionUpvote
from app.schemas.skills import (
    ContributeQuestionRequest,
    ContributeQuestionResponse,
    QuestionResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.memory.skill_graph import skill_graph_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/questions", tags=["questions"])


# ── GET /api/v1/questions/next ────────────────────────────────────────────────


@router.get("/next", response_model=QuestionResponse)
async def get_next_question(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    skill: str | None = Query(None, description="Target a specific skill"),
    type: str | None = Query(None, description="behavioral | system_design | coding_discussion"),
    company: str | None = Query(None, description="Prefer questions tagged for this company"),
) -> QuestionResponse:
    """Return the next adaptive question based on the user's weakest skills.

    Selection priority:
    1. If `company` specified → prefer company-tagged questions.
    2. If `skill` specified → filter by that skill.
    3. Else → pick from the user's weakest 3 skills.
    4. Prefer questions not recently used (least-used first).
    5. Random selection within matching set to avoid repetition.
    """
    if skill:
        target_skills = [skill]
    else:
        # Get weakest skills from graph
        weak_nodes = await skill_graph_service.get_weakest_skills(db, current_user.id, limit=3)
        target_skills = [n.skill_name for n in weak_nodes]

    # Try company-specific questions first when company is specified
    question: Question | None = None
    if company:
        question = await _select_question(db, target_skills, question_type=type, company=company)

    if question is None:
        question = await _select_question(db, target_skills, question_type=type)

    if question is None:
        # Fallback: any question of requested type
        question = await _select_question(db, [], question_type=type)

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions found. Run the seed script to populate the question bank.",
        )

    # Increment usage count
    question.times_used = (question.times_used or 0) + 1
    await db.commit()

    logger.info(
        "questions.next_selected",
        user_id=str(current_user.id),
        question_id=str(question.id),
        target_skills=target_skills,
        question_type=question.type,
    )

    return QuestionResponse.model_validate(question)


# ── GET /api/v1/questions ─────────────────────────────────────────────────────


@router.get("", response_model=list[QuestionResponse])
async def list_questions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    type: str | None = Query(None),
    difficulty: str | None = Query(None),
    company: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
) -> list[QuestionResponse]:
    """Browse the question bank with optional filters."""
    stmt = select(Question)

    if type:
        stmt = stmt.where(Question.type == type)
    if difficulty:
        stmt = stmt.where(Question.difficulty == difficulty)
    if company:
        stmt = stmt.where(Question.company == company)

    stmt = stmt.order_by(Question.created_at).limit(limit).offset(offset)
    result = await db.execute(stmt)
    questions = list(result.scalars().all())

    return [QuestionResponse.model_validate(q) for q in questions]


# ── POST /api/v1/questions/contribute ────────────────────────────────────────


@router.post(
    "/contribute", response_model=ContributeQuestionResponse, status_code=status.HTTP_201_CREATED
)
async def contribute_question(
    body: ContributeQuestionRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContributeQuestionResponse:
    """Submit a new question for admin review.

    The question is created with status='pending' and will be reviewed
    before appearing in the question bank.
    """
    valid_types = {
        "behavioral",
        "system_design",
        "coding_discussion",
        "negotiation",
        "diagnostic",
        "debrief",
    }
    valid_difficulties = {"l4", "l5", "l6"}

    if body.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid type. Must be one of: {sorted(valid_types)}",
        )
    if body.difficulty not in valid_difficulties:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="difficulty must be l4, l5, or l6",
        )
    if len(body.text.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question text must be at least 10 characters.",
        )

    question = Question(
        text=body.text.strip(),
        type=body.type,
        difficulty=body.difficulty,
        skills_tested=body.skills_tested,
        company=body.company,
        submitted_by=current_user.id,
        status="pending",
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)

    logger.info(
        "questions.contributed",
        user_id=str(current_user.id),
        question_id=str(question.id),
        question_type=question.type,
    )

    return ContributeQuestionResponse(
        id=question.id,
        status="pending",
        message="Your question is under review. Thank you for contributing!",
    )


# ── GET /api/v1/questions/contribute ─────────────────────────────────────────


@router.get("/contribute", response_model=list[QuestionResponse])
async def list_my_contributions(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[QuestionResponse]:
    """Return all questions submitted by the current user."""
    result = await db.execute(
        select(Question)
        .where(Question.submitted_by == current_user.id)
        .order_by(Question.created_at.desc())
    )
    return [QuestionResponse.model_validate(q) for q in result.scalars().all()]


# ── POST /api/v1/questions/{id}/upvote ───────────────────────────────────────


@router.post("/{question_id}/upvote", status_code=status.HTTP_204_NO_CONTENT)
async def upvote_question(
    question_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Upvote a question. Each user can upvote a given question once."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    question = result.scalar_one_or_none()
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")

    upvote = QuestionUpvote(question_id=question_id, user_id=current_user.id)
    db.add(upvote)
    try:
        question.upvotes = (question.upvotes or 0) + 1
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already upvoted this question.",
        )


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _select_question(
    db: AsyncSession,
    target_skills: list[str],
    question_type: str | None = None,
    company: str | None = None,
) -> Question | None:
    """Select an approved question targeting the given skills, least-used first.

    When `company` is specified, restricts to company-tagged questions only.
    """
    stmt = select(Question).where(Question.status == "approved")

    if question_type:
        stmt = stmt.where(Question.type == question_type)

    if company:
        stmt = stmt.where(Question.company == company)

    limit = 50 if target_skills else 20
    stmt = stmt.order_by(Question.times_used, func.random()).limit(limit)

    result = await db.execute(stmt)
    candidates: list[Question] = list(result.scalars().all())

    if not candidates:
        return None

    if target_skills:
        # Filter for skill overlap (client-side for MVP simplicity)
        target_set = set(target_skills)
        matching = [q for q in candidates if target_set & set(q.skills_tested or [])]
        if matching:
            return matching[0]  # already sorted by times_used, random

    return candidates[0] if candidates else None
