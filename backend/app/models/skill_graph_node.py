"""SkillGraphNode — one row per user per microskill.

20-30 microskills defined in spec Component 5.
Spaced repetition: low score + declining trend → practice sooner.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class SkillTrend:
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"


# All 20-30 microskills from spec Part 1 Component 5
SKILL_CATEGORIES = {
    "system_design": [
        "capacity_estimation",
        "tradeoff_analysis",
        "component_design",
        "api_design",
        "scalability_thinking",
        "failure_modes",
    ],
    "behavioral": [
        "star_structure",
        "quantifiable_results",
        "ownership_signal",
        "conflict_resolution",
        "leadership_stories",
        "mentoring_signal",
    ],
    "communication": [
        "conciseness",
        "filler_word_control",
        "pacing",
        "confidence_under_pressure",
    ],
    "coding_discussion": [
        "complexity_analysis",
        "edge_cases",
        "testing_approach",
        "code_review_reasoning",
    ],
    "negotiation": [
        "anchoring",
        "value_articulation",
        "counter_strategy",
        "emotional_control",
    ],
}


class SkillGraphNode(Base):
    __tablename__ = "skill_graph"
    __table_args__ = (
        UniqueConstraint("user_id", "skill_name", name="uq_skill_graph_user_skill"),
        {"comment": "One row per user per microskill. Spaced repetition drives drill plan."},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    skill_name: Mapped[str] = mapped_column(String(100), nullable=False)
    skill_category: Mapped[str] = mapped_column(String(100), nullable=False)

    current_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    trend: Mapped[str] = mapped_column(String(20), nullable=False, default=SkillTrend.STABLE)

    # [{session, timestamp_ms, score, date}]
    evidence_links: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    # ["forgets to mention rejected alternatives"]
    typical_mistakes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    last_practiced: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_due: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="skill_graph_nodes")

    def __repr__(self) -> str:
        return f"<SkillGraphNode {self.skill_name} score={self.current_score} trend={self.trend}>"
