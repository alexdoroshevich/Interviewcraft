"""Pydantic schemas for session endpoints."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    type: str = Field(
        ...,
        pattern="^(behavioral|system_design|coding_discussion|negotiation|diagnostic|debrief)$",
        description="Interview session type",
    )
    interview_type: str | None = None
    quality_profile: str = Field(
        default="balanced",
        pattern="^(quality|balanced|budget)$",
    )
    voice_id: str | None = None
    persona: str = Field(
        default="neutral",
        pattern="^(neutral|friendly|tough)$",
    )
    company: str | None = Field(
        default=None,
        pattern="^(google|meta|amazon|microsoft|apple|netflix|uber|stripe|linkedin|airbnb|nvidia|spotify)$",
    )
    focus_skill: str | None = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    type: str
    interview_type: str | None
    status: str
    quality_profile: str
    voice_id: str | None
    persona: str
    company: str | None
    focus_skill: str | None
    total_cost_usd: Decimal
    created_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class SessionDetail(SessionResponse):
    """Full session with transcript (for session detail view)."""

    transcript: list[Any]
    lint_results: dict[str, Any] | None


class SessionEnd(BaseModel):
    """Body for PATCH /sessions/{id} to end a session."""

    status: str = Field(default="completed", pattern="^(completed|abandoned)$")


class JdAnalysisRequest(BaseModel):
    """Body for POST /api/v1/sessions/analyze-jd."""

    jd_text: str = Field(..., min_length=50, max_length=8000, description="Job description text")


class JdFocusArea(BaseModel):
    area: str  # e.g. "System design at scale"
    reason: str  # Why this matters for the role
    priority: str  # "high" | "medium" | "low"


class JdAnalysisResponse(BaseModel):
    """Structured analysis of a job description."""

    skills_required: list[str]
    skills_nice_to_have: list[str]
    seniority: str  # junior | mid | senior | staff | principal | unknown
    role_type: str  # backend | frontend | fullstack | ml | data | mobile | devops | other
    suggested_session_type: str  # behavioral | system_design | coding_discussion | negotiation
    suggested_company: str | None  # detected company slug or None
    focus_areas: list[JdFocusArea]
    coaching_note: str  # 1-2 sentence preparation tip
    input_tokens: int = 0
    output_tokens: int = 0
