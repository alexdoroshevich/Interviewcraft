"""Pydantic schemas for share card endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class ShareCardSnapshot(BaseModel):
    """Point-in-time snapshot of a user's readiness, stored in share_cards.snapshot_data."""

    readiness_score: int
    avg_skill_score: float
    skill_scores_by_category: dict[str, float]
    top_strengths: list[str]
    session_count: int
    generated_at: str


class ShareCardCreateResponse(BaseModel):
    """Returned when a user creates a new share card."""

    token: str
    share_url: str
    expires_at: str | None


class ShareCardPublicResponse(BaseModel):
    """Public view of a share card — no auth required to read."""

    token: str
    snapshot: ShareCardSnapshot
    created_at: str
    expires_at: str | None
