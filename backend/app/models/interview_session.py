"""InterviewSession model — one session = one mock interview or negotiation round."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.segment_score import SegmentScore
    from app.models.session_metrics import SessionMetrics
    from app.models.transcript_word import TranscriptWord
    from app.models.usage_log import UsageLog
    from app.models.user import User


class SessionType:
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    CODING_DISCUSSION = "coding_discussion"
    NEGOTIATION = "negotiation"
    DIAGNOSTIC = "diagnostic"


class SessionStatus:
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QualityProfile:
    QUALITY = "quality"  # Sonnet all tasks + ElevenLabs (~$0.60–1.30/session)
    BALANCED = "balanced"  # Sonnet voice, Haiku scoring/diff/memory (~$0.30–0.60)
    BUDGET = "budget"  # Haiku all + Deepgram Aura-1 TTS (~$0.15–0.30)


class PersonaType:
    NEUTRAL = "neutral"  # Balanced, professional (default)
    FRIENDLY = "friendly"  # Warm, encouraging, more patient
    TOUGH = "tough"  # Challenging, skeptical, pushes harder


class CompanyType:
    GOOGLE = "google"
    META = "meta"
    AMAZON = "amazon"
    MICROSOFT = "microsoft"
    APPLE = "apple"
    NETFLIX = "netflix"


class InterviewSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    interview_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SessionStatus.ACTIVE, index=True
    )
    quality_profile: Mapped[str] = mapped_column(
        String(20), nullable=False, default=QualityProfile.BALANCED
    )
    voice_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    persona: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PersonaType.NEUTRAL, server_default="neutral"
    )
    company: Mapped[str | None] = mapped_column(String(30), nullable=True)
    focus_skill: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Full transcript stored as JSONB array of {role, text, timestamp_ms}
    # Word-level timestamps go in transcript_words table (TTL 14d), NOT here
    transcript: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)

    # Post-session lint results (populated after session ends)
    lint_results: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    segment_scores: Mapped[list["SegmentScore"]] = relationship(
        "SegmentScore", back_populates="session", cascade="all, delete-orphan"
    )
    metrics: Mapped[list["SessionMetrics"]] = relationship(
        "SessionMetrics", back_populates="session", cascade="all, delete-orphan"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship("UsageLog", back_populates="session")
    transcript_words: Mapped[list["TranscriptWord"]] = relationship(
        "TranscriptWord", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<InterviewSession id={self.id} type={self.type} status={self.status}>"
