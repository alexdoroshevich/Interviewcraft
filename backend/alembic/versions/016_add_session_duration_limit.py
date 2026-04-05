"""Add duration_limit_minutes to sessions table.

Revision ID: 016
Revises: 015
Create Date: 2026-04-05
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("duration_limit_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "duration_limit_minutes")
