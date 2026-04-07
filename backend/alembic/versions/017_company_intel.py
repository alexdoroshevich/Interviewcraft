"""Add company_intel table for community interview insights.

Revision ID: 017
Revises: 016
Create Date: 2026-04-06
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "017"
down_revision: str = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_intel",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company", sa.String(100), nullable=False),
        sa.Column(
            "category",
            sa.String(30),
            nullable=False,
            server_default="process",
        ),  # process | technical | culture | tips
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("upvotes", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="approved",
        ),  # pending | approved | rejected
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_company_intel_company", "company_intel", ["company"])
    op.create_index("idx_company_intel_status", "company_intel", ["status"])


def downgrade() -> None:
    op.drop_index("idx_company_intel_status", table_name="company_intel")
    op.drop_index("idx_company_intel_company", table_name="company_intel")
    op.drop_table("company_intel")
