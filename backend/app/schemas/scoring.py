"""Pydantic schemas for the scoring API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvidenceSpan(BaseModel):
    start_ms: int
    end_ms: int
    server_extracted_quote: str | None = None


class RuleTriggered(BaseModel):
    rule: str
    confidence: str  # "strong" | "weak"
    evidence: EvidenceSpan
    fix: str
    impact: str


class CategoryScores(BaseModel):
    structure: int
    depth: int
    communication: int
    seniority_signal: int


class LevelAssessment(BaseModel):
    l4: str  # "pass" | "borderline" | "fail"
    l5: str
    l6: str
    gaps: list[str] = Field(default_factory=list)


class DiffChange(BaseModel):
    before: str
    after: str
    rule: str
    impact: str


class DiffVersion(BaseModel):
    text: str
    changes: list[DiffChange] = Field(default_factory=list)
    estimated_new_score: int


class DiffVersions(BaseModel):
    minimal: DiffVersion
    medium: DiffVersion
    ideal: DiffVersion


class MemoryHint(BaseModel):
    skill: str
    direction: str  # "positive" | "negative"
    note: str


class MemoryHints(BaseModel):
    skill_signals: list[MemoryHint] = Field(default_factory=list)
    story_detected: bool = False
    story_title: str | None = None
    communication_notes: str | None = None


class SegmentScoreResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    segment_index: int
    question_text: str
    answer_text: str
    overall_score: int
    confidence: str
    category_scores: dict[str, Any]
    rules_triggered: list[Any]
    level_assessment: dict[str, Any]
    diff_versions: dict[str, Any] | None
    rewind_count: int
    best_rewind_score: int | None
    created_at: datetime

    model_config = {"from_attributes": True}


class HesitationGapResponse(BaseModel):
    start_ms: int
    end_ms: int
    duration_ms: int


class DeliveryAnalysisResponse(BaseModel):
    """Delivery metrics for a session — filler words, WPM, hesitation gaps."""

    total_words: int
    duration_seconds: float
    wpm: float
    filler_count: int
    filler_rate: float
    fillers_by_type: dict[str, int]
    top_filler: str | None
    hesitation_gaps: list[dict[str, int]]
    long_pause_count: int
    has_word_timestamps: bool
    delivery_score: int
    delivery_grade: str
    coaching_tips: list[str]


class ScoringRequest(BaseModel):
    """Body for POST /sessions/{id}/score — usually empty (uses session transcript)."""

    force_rescore: bool = False  # Re-score even if lint_results already exists


class ScoringStatusResponse(BaseModel):
    session_id: uuid.UUID
    segments_scored: int
    total_cost_usd: float
    cache_hit_tokens: int
    scores: list[SegmentScoreResponse]
