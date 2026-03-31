"""Initial schema — all MVP tables.

Revision ID: 001
Revises:
Create Date: 2026-02-24

Tables: users, sessions, segment_scores, transcript_words,
        skill_graph, questions, session_metrics, usage_logs
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── pgcrypto for gen_random_uuid() ─────────────────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # ── user_role enum ─────────────────────────────────────────────────────────
    user_role = postgresql.ENUM("user", "admin", name="user_role", create_type=False)
    user_role.create(op.get_bind(), checkfirst=True)

    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column(
            "role",
            postgresql.ENUM("user", "admin", name="user_role", create_type=False),
            nullable=False,
            server_default="user",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("failed_login_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("google_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index(
        "idx_users_google_id",
        "users",
        ["google_id"],
        postgresql_where=sa.text("google_id IS NOT NULL"),
    )

    # ── sessions ───────────────────────────────────────────────────────────────
    op.create_table(
        "sessions",
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
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("interview_type", sa.String(100), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("quality_profile", sa.String(20), nullable=False, server_default="balanced"),
        # Word-level timestamps go in transcript_words (TTL 14d), NOT here
        sa.Column(
            "transcript",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "lint_results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "total_cost_usd",
            sa.Numeric(10, 6),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_sessions_user_id", "sessions", ["user_id"])
    op.create_index("idx_sessions_status", "sessions", ["status"])
    op.create_index("idx_sessions_created_at", "sessions", ["created_at"])

    # ── segment_scores ─────────────────────────────────────────────────────────
    op.create_table(
        "segment_scores",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_index", sa.Integer, nullable=False),
        sa.Column("question_text", sa.Text, nullable=False),
        sa.Column("answer_text", sa.Text, nullable=False),
        sa.Column("overall_score", sa.Integer, nullable=False),
        sa.Column("confidence", sa.Text, nullable=False, server_default="medium"),
        sa.Column(
            "category_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "rules_triggered",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "level_assessment",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "diff_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("rewind_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("best_rewind_score", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_segment_scores_session_id", "segment_scores", ["session_id"])

    # ── transcript_words (TTL 14 days — SEPARATE from session JSONB) ───────────
    op.create_table(
        "transcript_words",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("word", sa.String(255), nullable=False),
        sa.Column("start_ms", sa.Integer, nullable=False),
        sa.Column("end_ms", sa.Integer, nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("speaker", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_transcript_words_session_id", "transcript_words", ["session_id"])
    # Index on expires_at so the TTL cleanup job runs efficiently
    op.create_index("idx_transcript_words_expires_at", "transcript_words", ["expires_at"])

    # ── skill_graph ────────────────────────────────────────────────────────────
    op.create_table(
        "skill_graph",
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
        sa.Column("skill_name", sa.String(100), nullable=False),
        sa.Column("skill_category", sa.String(100), nullable=False),
        sa.Column("current_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("best_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("trend", sa.String(20), nullable=False, server_default="stable"),
        sa.Column(
            "evidence_links",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "typical_mistakes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("last_practiced", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_due", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_skill_graph_user_id", "skill_graph", ["user_id"])
    op.create_unique_constraint(
        "uq_skill_graph_user_skill", "skill_graph", ["user_id", "skill_name"]
    )

    # ── questions ──────────────────────────────────────────────────────────────
    op.create_table(
        "questions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("difficulty", sa.String(10), nullable=False, server_default="l5"),
        sa.Column(
            "skills_tested",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("times_used", sa.Integer, nullable=False, server_default="0"),
        # Reserved for ChromaDB reference — populated Weeks 5-6
        sa.Column("embedding_id", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_questions_type", "questions", ["type"])
    op.create_index("idx_questions_difficulty", "questions", ["difficulty"])

    # ── session_metrics ────────────────────────────────────────────────────────
    op.create_table(
        "session_metrics",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("segment_index", sa.Integer, nullable=True),
        sa.Column("stt_latency_ms", sa.Integer, nullable=True),
        sa.Column("llm_ttft_ms", sa.Integer, nullable=True),
        sa.Column("tts_latency_ms", sa.Integer, nullable=True),
        sa.Column("e2e_latency_ms", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_session_metrics_session_id", "session_metrics", ["session_id"])
    op.create_index("idx_session_metrics_created_at", "session_metrics", ["created_at"])

    # ── usage_logs ─────────────────────────────────────────────────────────────
    op.create_table(
        "usage_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("operation", sa.String(100), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("cached_tokens", sa.Integer, nullable=True),
        sa.Column("audio_seconds", sa.Float, nullable=True),
        sa.Column("characters", sa.Integer, nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False),
        sa.Column("latency_ms", sa.Integer, nullable=False),
        sa.Column("quality_profile", sa.String(20), nullable=True),
        sa.Column("cached", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index("idx_usage_logs_session_id", "usage_logs", ["session_id"])
    op.create_index("idx_usage_logs_user_id", "usage_logs", ["user_id"])
    op.create_index("idx_usage_logs_created_at", "usage_logs", ["created_at"])
    op.create_index("idx_usage_logs_provider", "usage_logs", ["provider"])


def downgrade() -> None:
    op.drop_table("usage_logs")
    op.drop_table("session_metrics")
    op.drop_table("questions")
    op.drop_table("skill_graph")
    op.drop_table("transcript_words")
    op.drop_table("segment_scores")
    op.drop_table("sessions")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
