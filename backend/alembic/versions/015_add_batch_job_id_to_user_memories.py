"""Add batch_job_id to user_memories for Batch API consolidation.

Revision ID: 015
Revises: 014
Create Date: 2026-04-06
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_memories",
        sa.Column("batch_job_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_memories", "batch_job_id")
