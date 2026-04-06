"""Story Bank API — CRUD + coverage map + story proposals.

GET    /api/v1/stories              — list user's stories
POST   /api/v1/stories              — create story manually
PUT    /api/v1/stories/{id}         — update story
DELETE /api/v1/stories/{id}         — delete story
GET    /api/v1/stories/coverage     — behavioral competency coverage map
POST   /api/v1/stories/propose      — propose story from session (auto-detect)
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.story import COMPETENCIES, OVERUSE_THRESHOLD, Story
from app.schemas.stories import (
    CompetencyCoverage,
    CoverageMapResponse,
    StoryCreate,
    StoryProposalResponse,
    StoryProposeRequest,
    StoryResponse,
    StoryUpdate,
)
from app.services.auth.dependencies import CurrentUser
from app.services.memory.story_extractor import StoryExtractor

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/stories", tags=["stories"])


# ── GET /api/v1/stories ───────────────────────────────────────────────────────


@router.get("", response_model=list[StoryResponse])
async def list_stories(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[StoryResponse]:
    """List all stories for the current user, newest first."""
    result = await db.execute(
        select(Story).where(Story.user_id == current_user.id).order_by(Story.created_at.desc())
    )
    stories = list(result.scalars().all())
    return [StoryResponse.model_validate(s) for s in stories]


# ── POST /api/v1/stories ──────────────────────────────────────────────────────


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    body: StoryCreate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StoryResponse:
    """Create a story manually or save an auto-detected proposal."""
    story = Story(
        user_id=current_user.id,
        title=body.title,
        summary=body.summary,
        competencies=body.competencies,
        source_session_id=body.source_session_id,
        auto_detected=body.auto_detected,
        warnings=[],
    )
    db.add(story)
    await db.commit()
    await db.refresh(story)

    logger.info(
        "stories.created",
        user_id=str(current_user.id),
        story_id=str(story.id),
        competencies=body.competencies,
        auto_detected=body.auto_detected,
    )

    return StoryResponse.model_validate(story)


# ── PUT /api/v1/stories/{id} ──────────────────────────────────────────────────


@router.put("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: uuid.UUID,
    body: StoryUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StoryResponse:
    """Update a story's title, summary, or competencies."""
    story = await _get_owned_story(db, story_id, current_user.id)

    if body.title is not None:
        story.title = body.title
    if body.summary is not None:
        story.summary = body.summary
    if body.competencies is not None:
        story.competencies = body.competencies
        # Recompute warnings
        story.warnings = _compute_warnings(story)

    await db.commit()
    await db.refresh(story)
    return StoryResponse.model_validate(story)


# ── DELETE /api/v1/stories/{id} ───────────────────────────────────────────────


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(
    story_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete a story permanently."""
    story = await _get_owned_story(db, story_id, current_user.id)
    await db.delete(story)
    await db.commit()
    logger.info("stories.deleted", user_id=str(current_user.id), story_id=str(story_id))


# ── GET /api/v1/stories/coverage ─────────────────────────────────────────────


@router.get("/coverage", response_model=CoverageMapResponse)
async def get_coverage_map(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CoverageMapResponse:
    """Return the behavioral competency coverage map."""
    result = await db.execute(select(Story).where(Story.user_id == current_user.id))
    stories = list(result.scalars().all())

    # Build coverage per competency
    coverage_items: list[CompetencyCoverage] = []
    covered = 0
    gaps = 0

    for comp in COMPETENCIES:
        comp_stories = [s for s in stories if comp in (s.competencies or [])]
        story_count = len(comp_stories)

        if story_count == 0:
            status_val = "gap"
            gaps += 1
            action = (
                f"No story for '{comp.replace('_', ' ')}' — "
                f"this is commonly asked in L5+ interviews. Create one."
            )
        elif any(
            s.best_score_with_this_story is not None and s.best_score_with_this_story < 65
            for s in comp_stories
        ):
            status_val = "weak"
            covered += 1
            action = (
                f"Your '{comp.replace('_', ' ')}' story scores below 65. "
                f"Practice it with Rewind to strengthen."
            )
        else:
            status_val = "strong"
            covered += 1
            action = None

        coverage_items.append(
            CompetencyCoverage(
                competency=comp,
                status=status_val,
                story_count=story_count,
                stories=[
                    {
                        "id": str(s.id),
                        "title": s.title,
                        "times_used": s.times_used,
                        "best_score": s.best_score_with_this_story,
                    }
                    for s in comp_stories
                ],
                action=action,
            )
        )

    total = len(COMPETENCIES)
    return CoverageMapResponse(
        competencies=coverage_items,
        total_stories=len(stories),
        covered=covered,
        gaps=gaps,
        coverage_pct=round(covered / total * 100, 1) if total else 0.0,
    )


# ── POST /api/v1/stories/propose ─────────────────────────────────────────────


@router.post("/propose", response_model=StoryProposalResponse | None)
async def propose_story(
    body: StoryProposeRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StoryProposalResponse | None:
    """Auto-detect and propose a story from a completed session.

    Returns null if no story detected or already saved.
    """
    from app.models.interview_session import InterviewSession

    session_id = body.session_id

    result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == current_user.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    extractor = StoryExtractor(api_key=settings.anthropic_api_key)
    proposal = await extractor.extract_story_proposal(
        db=db,
        user_id=current_user.id,
        session_id=session_id,
        transcript=session.transcript or [],
    )

    if proposal is None:
        return None

    return StoryProposalResponse(**proposal)


# ── Helpers ────────────────────────────────────────────────────────────────────


async def _get_owned_story(
    db: AsyncSession,
    story_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Story:
    result = await db.execute(select(Story).where(Story.id == story_id, Story.user_id == user_id))
    story = result.scalar_one_or_none()
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


def _compute_warnings(story: Story) -> list[str]:
    """Recompute warning flags for a story."""
    warnings = []
    if (story.times_used or 0) >= OVERUSE_THRESHOLD:
        comps = ", ".join(story.competencies or [])
        warnings.append(f"OVERUSED ({story.times_used}x) — prepare an alternative for: {comps}")
    return warnings
