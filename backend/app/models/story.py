"""Story — user's Story Bank entry.

Stories are semi-automatically extracted from session transcripts when
memory_extractor detects story_detected=True. Users one-click save them.

Each story maps to 1+ behavioral competencies (coverage map).
Overuse warning fires when times_used >= 3 for the same competency.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

if TYPE_CHECKING:
    pass


# ── Behavioral competencies used in Coverage Map ──────────────────────────────
# These map to STAR-story categories (not the same as microskills).

COMPETENCIES = [
    "technical_leadership",
    "execution",
    "cross_team",
    "conflict_resolution",
    "mentoring",
    "failure_recovery",
    "innovation",
    "communication",
    "data_driven_decision",
    "customer_focus",
]

# Overuse threshold: same story used 3+ times → generate warning
OVERUSE_THRESHOLD = 3


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Which behavioral competencies this story demonstrates
    # e.g. ["technical_leadership", "cross_team"]
    competencies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Usage tracking
    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    best_score_with_this_story: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Auto-generated warnings (e.g., overuse)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    # Source session where this story was detected (optional)
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )

    # Whether this was auto-detected (True) or manually created (False)
    auto_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<Story id={self.id} title={self.title!r} competencies={self.competencies}>"
