"""Pydantic schemas for Story Bank and Coverage Map."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

# ── Story CRUD ────────────────────────────────────────────────────────────────


class StoryProposeRequest(BaseModel):
    """Body for POST /api/v1/stories/propose."""

    session_id: uuid.UUID


class StoryCreate(BaseModel):
    """Body for POST /api/v1/stories."""

    title: str
    summary: str
    competencies: list[str]
    source_session_id: uuid.UUID | None = None
    auto_detected: bool = False


class StoryUpdate(BaseModel):
    """Body for PUT /api/v1/stories/{id}."""

    title: str | None = None
    summary: str | None = None
    competencies: list[str] | None = None


class StoryResponse(BaseModel):
    """Story as returned by API."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    summary: str
    competencies: list[str]
    times_used: int
    last_used: datetime | None
    best_score_with_this_story: int | None
    warnings: list[str]
    source_session_id: uuid.UUID | None
    auto_detected: bool
    created_at: datetime
    updated_at: datetime


# ── Coverage Map ──────────────────────────────────────────────────────────────


class CompetencyCoverage(BaseModel):
    """Coverage status for a single behavioral competency."""

    competency: str
    status: str  # "strong" | "weak" | "gap"
    story_count: int
    stories: list[dict[str, Any]]  # [{id, title, times_used, best_score}]
    action: str | None  # suggested action if gap or weak


class CoverageMapResponse(BaseModel):
    """Full coverage map for a user."""

    competencies: list[CompetencyCoverage]
    total_stories: int
    covered: int  # competencies with at least 1 story
    gaps: int  # competencies with no stories
    coverage_pct: float  # covered / total * 100


# ── Story proposal (from session auto-detection) ──────────────────────────────


class StoryProposalResponse(BaseModel):
    """Proposed story from session transcript analysis."""

    session_id: uuid.UUID
    proposed_title: str
    proposed_summary: str
    proposed_competencies: list[str]
    already_saved: bool
