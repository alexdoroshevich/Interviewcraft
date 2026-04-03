"""User model — authentication, roles, lockout state."""

import enum
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession
    from app.models.share_card import ShareCard
    from app.models.skill_graph_node import SkillGraphNode
    from app.models.usage_log import UsageLog
    from app.models.user_memory import UserMemory


class UserRole(enum.StrEnum):
    user = "user"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.user
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Lockout tracking
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Profile (parsed resume data)
    profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=None)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    # BYOK — encrypted API keys (Fernet-encrypted values keyed by provider name)
    byok_keys: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=None)

    # OAuth
    google_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    sessions: Mapped[list["InterviewSession"]] = relationship(
        "InterviewSession", back_populates="user", cascade="all, delete-orphan"
    )
    skill_graph_nodes: Mapped[list["SkillGraphNode"]] = relationship(
        "SkillGraphNode", back_populates="user", cascade="all, delete-orphan"
    )
    usage_logs: Mapped[list["UsageLog"]] = relationship("UsageLog", back_populates="user")
    share_cards: Mapped[list["ShareCard"]] = relationship(
        "ShareCard", back_populates="user", cascade="all, delete-orphan"
    )
    user_memory: Mapped["UserMemory | None"] = relationship(
        "UserMemory", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def is_locked(self) -> bool:
        """Return True if the account is currently locked out."""
        if self.locked_until is None:
            return False
        return datetime.now(tz=UTC) < self.locked_until

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
