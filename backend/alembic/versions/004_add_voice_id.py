"""Add voice_id column to sessions table.

Revision ID: 004
Revises: 003
"""

import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("voice_id", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "voice_id")
