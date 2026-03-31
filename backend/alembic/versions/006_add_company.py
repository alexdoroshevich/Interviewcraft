"""Add company column to sessions.

Revision ID: 006
Revises: 005
Create Date: 2026-03-15
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("company", sa.String(30), nullable=True, server_default=None),
    )


def downgrade() -> None:
    op.drop_column("sessions", "company")
