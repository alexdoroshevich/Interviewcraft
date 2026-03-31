"""Profile endpoints — self-assessment for onboarding.

Stores diagnostic self-assessment in the user.profile JSONB field
under the 'self_assessment' key. This data feeds the drill planner
to personalize practice recommendations.
"""

from datetime import UTC, datetime
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.profile import (
    SelfAssessmentRequest,
    SelfAssessmentResponse,
    SelfAssessmentStatus,
)
from app.services.auth.dependencies import CurrentUser

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

# Allowed weak-area values (validated server-side)
_VALID_WEAK_AREAS = frozenset(
    {
        "star_structure",
        "quantifiable_results",
        "tradeoff_analysis",
        "system_design",
        "coding_discussion",
        "data_structures",
        "conciseness",
        "filler_words",
        "ownership",
        "scalability_thinking",
        "leadership",
        "mentoring",
        "negotiation",
    }
)


# ── POST /self-assessment ─────────────────────────────────────────────────────


@router.post(
    "/self-assessment",
    response_model=SelfAssessmentResponse,
    status_code=status.HTTP_200_OK,
)
async def save_self_assessment(
    body: SelfAssessmentRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SelfAssessmentResponse:
    """Save or overwrite the user's diagnostic self-assessment."""
    # Validate weak_areas values
    invalid = set(body.weak_areas) - _VALID_WEAK_AREAS
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid weak areas: {', '.join(sorted(invalid))}",
        )

    now = datetime.now(tz=UTC)

    assessment_data = {
        "target_company": body.target_company,
        "target_level": body.target_level,
        "weak_areas": body.weak_areas,
        "interview_timeline": body.interview_timeline,
        "completed_at": now.isoformat(),
    }

    # Merge into existing profile JSONB (preserve other keys like resume data)
    profile = dict(current_user.profile) if current_user.profile else {}
    profile["self_assessment"] = assessment_data
    current_user.profile = profile

    await db.commit()
    await db.refresh(current_user)

    logger.info(
        "profile.self_assessment_saved",
        user_id=str(current_user.id),
        target_level=body.target_level,
        weak_areas_count=len(body.weak_areas),
        timeline=body.interview_timeline,
    )

    return SelfAssessmentResponse(
        target_company=body.target_company,
        target_level=body.target_level,
        weak_areas=body.weak_areas,
        interview_timeline=body.interview_timeline,
        completed_at=now,
    )


# ── GET /self-assessment ──────────────────────────────────────────────────────


@router.get(
    "/self-assessment",
    response_model=SelfAssessmentStatus,
)
async def get_self_assessment(
    current_user: CurrentUser,
) -> SelfAssessmentStatus:
    """Return the user's self-assessment if it exists."""
    profile = current_user.profile or {}
    sa = profile.get("self_assessment")

    if sa is None:
        return SelfAssessmentStatus(completed=False, data=None)

    return SelfAssessmentStatus(
        completed=True,
        data=SelfAssessmentResponse(
            target_company=sa["target_company"],
            target_level=sa["target_level"],
            weak_areas=sa["weak_areas"],
            interview_timeline=sa["interview_timeline"],
            completed_at=sa["completed_at"],
        ),
    )
