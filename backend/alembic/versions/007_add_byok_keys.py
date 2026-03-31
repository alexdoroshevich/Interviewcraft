"""Add byok_keys column to users table.

Revision ID: 007
Revises: 006
Create Date: 2026-03-16
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("byok_keys", postgresql.JSONB(), nullable=True, server_default=None),
    )


def downgrade() -> None:
    op.drop_column("users", "byok_keys")
