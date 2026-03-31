"""Question — bank of 200+ SWE interview questions.

ChromaDB embeddings added in Weeks 5-6 (embedding_id column reserved).
User-contributed questions added in P2-B (submitted_by, status, upvotes).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User

# Valid question statuses
QUESTION_STATUSES = ("pending", "approved", "rejected")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # behavioral | system_design | coding_discussion
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # l4 | l5 | l6
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="l5", index=True)

    # List of skill_name strings that this question tests
    skills_tested: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)

    # Optional company tag
    company: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)

    times_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Reserved for ChromaDB reference — populated in Weeks 5-6
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── User-contributed fields (P2-B) ────────────────────────────────────────
    # NULL = seed / admin-created question
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # pending | approved | rejected  (default approved for seed data)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="approved", index=True)
    upvotes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    submitter: Mapped[Optional["User"]] = relationship("User", foreign_keys=[submitted_by])
    upvote_records: Mapped[list["QuestionUpvote"]] = relationship(
        "QuestionUpvote", back_populates="question", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Question id={self.id} type={self.type} status={self.status}>"


class QuestionUpvote(Base):
    """One-upvote-per-user enforcement via unique constraint."""

    __tablename__ = "question_upvotes"
    __table_args__ = (UniqueConstraint("question_id", "user_id", name="uq_question_upvote"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    question: Mapped["Question"] = relationship("Question", back_populates="upvote_records")

    def __repr__(self) -> str:
        return f"<QuestionUpvote q={self.question_id} u={self.user_id}>"
