"""Add persona column to sessions table.

Revision ID: 005
Revises: 004
"""

import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("persona", sa.String(20), nullable=True, server_default="neutral"),
    )


def downgrade() -> None:
    op.drop_column("sessions", "persona")
