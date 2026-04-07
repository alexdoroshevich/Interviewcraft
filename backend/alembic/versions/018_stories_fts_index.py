"""Add GIN full-text search index on stories table.

Enables PostgreSQL FTS on story title + summary so the memory builder
can rank stories by semantic relevance when building best_stories context.
Uses to_tsvector('english', ...) — no extra extension needed.

Revision ID: 018
Revises: 017
"""

from alembic import op

revision: str = "018"
down_revision: str = "017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # CONCURRENTLY requires autocommit (cannot run inside a transaction)
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_stories_fts
            ON stories
            USING gin(
                to_tsvector(
                    'english',
                    coalesce(title, '') || ' ' || coalesce(summary, '')
                )
            )
            """
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_stories_fts")
