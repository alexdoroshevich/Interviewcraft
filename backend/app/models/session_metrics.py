"""SessionMetrics — latency measurements per voice exchange.

Every voice turn logs: stt_latency_ms, llm_ttft_ms, tts_latency_ms, e2e_latency_ms.
Used by the metrics dashboard to compute p50/p95 and hit the DoD KPI: p95 < 1000ms.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class SessionMetrics(Base):
    __tablename__ = "session_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # None for session-level metrics, set for per-segment metrics
    segment_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    stt_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    llm_ttft_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tts_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    e2e_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<SessionMetrics session={self.session_id} e2e={self.e2e_latency_ms}ms>"
