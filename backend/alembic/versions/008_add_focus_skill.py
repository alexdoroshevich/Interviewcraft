"""Add focus_skill column to sessions.

Revision ID: 008
Revises: 007
Create Date: 2026-03-17
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("focus_skill", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "focus_skill")
