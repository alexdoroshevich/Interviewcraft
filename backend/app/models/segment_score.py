"""SegmentScore — scoring result for one question-answer segment."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class SegmentScore(Base):
    __tablename__ = "segment_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    segment_index: Mapped[int] = mapped_column(Integer, nullable=False)

    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)

    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[str] = mapped_column(
        Text, nullable=False, default="medium"
    )  # high | medium | low

    # {structure: int, depth: int, communication: int, seniority_signal: int}
    category_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # List of {rule, confidence, evidence: {start_ms, end_ms, segment_id, server_extracted_quote}, fix, impact}
    rules_triggered: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    # {l4_pass: bool, l5_pass: bool, l5_borderline: bool, l6_pass: bool, gaps: [...]}
    level_assessment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # {minimal: {...}, medium: {...}, ideal: {...}} — populated by diff generator
    diff_versions: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Rewind tracking
    rewind_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_rewind_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="segment_scores"
    )

    def __repr__(self) -> str:
        return (
            f"<SegmentScore id={self.id} session={self.session_id} "
            f"idx={self.segment_index} score={self.overall_score}>"
        )
