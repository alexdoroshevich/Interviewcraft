"""Memory document schemas — what gets stored in user_memories.memory_document."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillSnapshot(BaseModel):
    """One skill's current state in memory."""

    skill: str
    score: int
    trend: str  # "improving" | "declining" | "stable"
    top_mistake: str | None = None
    sessions_practiced: int = 0


class StoryReference(BaseModel):
    """A story the user has used successfully."""

    title: str
    best_score: int
    competencies: list[str]
    tip: str | None = None


class CoachingInsight(BaseModel):
    """What coaching approaches work for this user."""

    insight: str
    evidence_count: int = 1


class MemoryDocument(BaseModel):
    """The complete memory document stored in user_memories.memory_document.

    Target: 2,000-3,000 tokens when serialized to the prompt block.
    """

    # Career context
    target_role: str | None = None
    target_level: str | None = None
    target_companies: list[str] = Field(default_factory=list, max_length=5)
    career_goal: str | None = None

    # Skill state (top 8 — full graph in skill_graph table)
    weakest_skills: list[SkillSnapshot] = Field(default_factory=list, max_length=4)
    strongest_skills: list[SkillSnapshot] = Field(default_factory=list, max_length=4)

    # Recurring patterns
    recurring_mistakes: list[str] = Field(default_factory=list, max_length=6)

    # Story bank highlights
    best_stories: list[StoryReference] = Field(default_factory=list, max_length=4)

    # Communication style
    communication_notes: list[str] = Field(default_factory=list, max_length=3)

    # Coaching effectiveness
    coaching_insights: list[CoachingInsight] = Field(default_factory=list, max_length=3)

    # Focus directive
    current_focus: str | None = None

    # Stats
    total_sessions: int = 0
    avg_score: int | None = None


class MemoryResponse(BaseModel):
    """GET /api/v1/settings/memory response."""

    memory: MemoryDocument
    version: int
    token_count: int
    total_sessions: int
    last_updated: str | None = None
