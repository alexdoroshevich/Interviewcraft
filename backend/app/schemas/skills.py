"""Pydantic schemas for skill graph, drill plan, rewind, and questions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

# ── Skill graph ────────────────────────────────────────────────────────────────


class SkillNodeResponse(BaseModel):
    """One microskill node in the user's skill graph."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    skill_name: str
    skill_category: str
    current_score: int
    best_score: int
    trend: str  # improving | declining | stable
    last_practiced: datetime | None
    next_review_due: datetime | None
    evidence_links: list[dict[str, Any]]
    typical_mistakes: list[str]
    created_at: datetime
    updated_at: datetime


class SkillGraphResponse(BaseModel):
    """Full skill graph for a user."""

    user_id: uuid.UUID
    total_skills: int
    nodes: list[SkillNodeResponse]
    # Overall stats
    avg_score: float
    weakest_category: str | None
    strongest_category: str | None


class SkillHistoryPoint(BaseModel):
    """One data point in a skill's history."""

    date: str  # ISO date string
    score: int
    session_id: str | None


class SkillHistoryResponse(BaseModel):
    """Trend history for a single skill."""

    skill_name: str
    current_score: int
    best_score: int
    trend: str
    history: list[SkillHistoryPoint]


# ── Drill plan ────────────────────────────────────────────────────────────────


class DrillSlot(BaseModel):
    """One practice slot in the weekly plan."""

    day: str
    skill_name: str
    skill_category: str
    current_score: int
    trend: str
    questions: int
    estimated_minutes: int
    focus_note: str


class DrillPlanResponse(BaseModel):
    """Weekly drill plan."""

    slots: list[DrillSlot]
    total_skills: int
    weakest_skill: str | None
    estimated_minutes_per_week: int
    generated_at: str
    message: str | None


class BeatYourBestItem(BaseModel):
    """One skill's Beat Your Best record."""

    skill_name: str
    skill_category: str
    current_score: int
    best_score: int
    gap: int
    can_beat: bool


class BenchmarkResponse(BaseModel):
    """Peer benchmark: where the current user ranks vs all users."""

    overall_percentile: int  # 0-100 — better than X% of users
    by_category: dict[str, int]  # category -> percentile
    your_avg_score: float
    platform_avg_score: float
    sample_size: int  # total users in the benchmark pool


# ── Rewind ────────────────────────────────────────────────────────────────────


class RewindStartResponse(BaseModel):
    """Response from POST /sessions/{id}/rewind — gives user context to re-answer."""

    segment_id: uuid.UUID
    question: str
    original_score: int
    original_answer_text: str
    hint: str
    rules_to_fix: list[str]  # rule_ids that triggered in original


class RewindScoreRequest(BaseModel):
    """Body for POST /sessions/{id}/rewind/{segment_id}/score."""

    answer_text: str


class CategoryDelta(BaseModel):
    structure: int = 0
    depth: int = 0
    communication: int = 0
    seniority_signal: int = 0


class RewindScoreResponse(BaseModel):
    """Result of a rewind re-scoring."""

    segment_id: uuid.UUID
    original_score: int
    new_score: int
    delta: int  # new - original (positive = improved)
    categories_delta: CategoryDelta
    rules_fixed: list[str]  # rules that were triggered before but not now
    rules_new: list[str]  # rules triggered now but not before
    reason: str  # human-readable explanation of the delta
    rewind_count: int
    best_rewind_score: int


# ── Questions ─────────────────────────────────────────────────────────────────


class QuestionResponse(BaseModel):
    """A single question from the question bank."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    type: str
    difficulty: str
    skills_tested: list[str]
    company: str | None = None
    status: str = "approved"
    upvotes: int = 0
    submitted_by: uuid.UUID | None = None


class ContributeQuestionRequest(BaseModel):
    """Body for POST /api/v1/questions/contribute."""

    text: str
    type: str  # behavioral | system_design | coding_discussion
    difficulty: str = "l5"  # l4 | l5 | l6
    skills_tested: list[str] = []
    company: str | None = None


class ContributeQuestionResponse(BaseModel):
    """Response when a user submits a new question."""

    id: uuid.UUID
    status: str
    message: str
