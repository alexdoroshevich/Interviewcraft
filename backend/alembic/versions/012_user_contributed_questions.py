"""Add user-contributed question support.

Adds submitted_by, status, and upvotes columns to questions table.
Creates question_upvotes junction table for one-vote-per-user enforcement.
Backfills all existing questions to status='approved'.

Revision ID: 012
Revises: 011
Create Date: 2026-03-29
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Add columns to questions ───────────────────────────────────────────────
    op.add_column(
        "questions",
        sa.Column(
            "submitted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "questions",
        sa.Column("status", sa.String(20), nullable=False, server_default="approved"),
    )
    op.add_column(
        "questions",
        sa.Column("upvotes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_questions_status", "questions", ["status"])
    op.create_index("ix_questions_submitted_by", "questions", ["submitted_by"])

    # Backfill all existing seed questions
    op.execute("UPDATE questions SET status = 'approved' WHERE status IS NULL OR status = ''")

    # ── Create question_upvotes junction table ────────────────────────────────
    op.create_table(
        "question_upvotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "question_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("question_id", "user_id", name="uq_question_upvote"),
    )
    op.create_index("ix_question_upvotes_question_id", "question_upvotes", ["question_id"])
    op.create_index("ix_question_upvotes_user_id", "question_upvotes", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_question_upvotes_user_id", table_name="question_upvotes")
    op.drop_index("ix_question_upvotes_question_id", table_name="question_upvotes")
    op.drop_table("question_upvotes")
    op.drop_index("ix_questions_submitted_by", table_name="questions")
    op.drop_index("ix_questions_status", table_name="questions")
    op.drop_column("questions", "upvotes")
    op.drop_column("questions", "status")
    op.drop_column("questions", "submitted_by")
