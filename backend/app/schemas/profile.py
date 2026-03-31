"""Pydantic schemas for user profile / self-assessment."""

from datetime import datetime

from pydantic import BaseModel, Field


class SelfAssessmentRequest(BaseModel):
    """Payload sent by the onboarding form."""

    target_company: str = Field(..., min_length=1, max_length=200)
    target_level: str = Field(
        ...,
        pattern=r"^(L3|L4|L5|L6|L7)$",
        description="Target seniority level (L3-L7)",
    )
    weak_areas: list[str] = Field(
        ...,
        min_length=1,
        description="At least one weak area must be selected",
    )
    interview_timeline: str = Field(
        ...,
        pattern=r"^(this_week|2_weeks|1_month|2_plus_months)$",
        description="When the interview is scheduled",
    )


class SelfAssessmentResponse(BaseModel):
    """Stored self-assessment data returned to the client."""

    target_company: str
    target_level: str
    weak_areas: list[str]
    interview_timeline: str
    completed_at: datetime


class SelfAssessmentStatus(BaseModel):
    """Minimal check for whether self-assessment is completed."""

    completed: bool
    data: SelfAssessmentResponse | None = None
