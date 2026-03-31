"""Add profile and resume_text columns to users table.

Revision ID: 003
Revises: 002
Create Date: 2026-02-26

Stores parsed resume data (JSONB) and raw extracted resume text.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True)
    )
    op.add_column("users", sa.Column("resume_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "resume_text")
    op.drop_column("users", "profile")
