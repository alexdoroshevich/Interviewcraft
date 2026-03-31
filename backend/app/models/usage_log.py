"""UsageLog — every API call cost logged here.

DoD requirement: Cost displayed in UI, matches profile.
Cache hit tracking → target cache hit rate > 70%.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession
    from app.models.user import User


class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Provider: anthropic | deepgram | elevenlabs
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # Operation: voice_llm | scoring_llm | diff_llm | memory_llm | stt | tts
    operation: Mapped[str] = mapped_column(String(100), nullable=False)

    # Token counts (Anthropic)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Deepgram STT
    audio_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ElevenLabs / Deepgram TTS
    characters: Mapped[int | None] = mapped_column(Integer, nullable=True)

    cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    # quality | balanced | budget
    quality_profile: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # True when Anthropic prompt cache was hit — tracked for cache hit rate KPI
    cached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    # Relationships
    session: Mapped[Optional["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="usage_logs"
    )
    user: Mapped[Optional["User"]] = relationship("User", back_populates="usage_logs")

    def __repr__(self) -> str:
        return (
            f"<UsageLog {self.provider}/{self.operation} "
            f"cost=${self.cost_usd} cached={self.cached}>"
        )
