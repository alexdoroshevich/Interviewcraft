"""Add share_cards table for public readiness snapshots.

Revision ID: 011
Revises: 010
Create Date: 2026-03-29
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "share_cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.String(40), nullable=False),
        sa.Column(
            "snapshot_data",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_share_cards_user_id", "share_cards", ["user_id"])
    op.create_index("ix_share_cards_token", "share_cards", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_share_cards_token", table_name="share_cards")
    op.drop_index("ix_share_cards_user_id", table_name="share_cards")
    op.drop_table("share_cards")
