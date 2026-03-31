"""Pydantic schemas for the Dashboard."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class RecentSession(BaseModel):
    """Compact session info for dashboard."""

    id: uuid.UUID
    type: str
    status: str
    created_at: datetime
    avg_score: int | None
    cost_usd: float


class DashboardResponse(BaseModel):
    """Main dashboard payload."""

    # Session stats
    total_sessions: int
    sessions_last_30_days: int
    sessions_scored: int

    # Score stats
    avg_score_all_time: float | None
    avg_score_last_30_days: float | None
    best_session_score: int | None

    # Skill graph summary
    total_skills_tracked: int
    avg_skill_score: float | None
    weakest_skill: str | None
    strongest_skill: str | None

    # Story bank
    total_stories: int
    coverage_pct: float

    # Negotiation
    total_negotiation_sessions: int
    avg_negotiation_score: float | None
    avg_money_left_on_table: int | None

    # Cost
    total_cost_usd: float
    cost_last_30_days: float

    # Readiness estimate (0-100 based on avg skill score + session count)
    readiness_estimate: int | None

    # Recent activity
    recent_sessions: list[RecentSession]
