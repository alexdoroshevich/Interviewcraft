"""Cost profile analysis for InterviewCraft usage_logs.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python benchmarks/cost-profile/query.py

WARNING: Output contains aggregated data. Do NOT commit output to results/.
         Use results/example.json for the committed example only.

Requires: sqlalchemy (already in backend deps)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _get_database_url() -> str:
    """Read DATABASE_URL from environment."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL env var not set", file=sys.stderr)
        print("Usage: DATABASE_URL=postgresql://... python benchmarks/cost-profile/query.py", file=sys.stderr)
        sys.exit(1)
    # sqlalchemy sync driver: swap asyncpg -> psycopg2
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return url


def run_queries() -> dict[str, object]:
    """Execute cost analysis queries against usage_logs and return results."""
    from sqlalchemy import create_engine, text  # noqa: PLC0415

    engine = create_engine(_get_database_url())
    results: dict[str, object] = {}

    with engine.connect() as conn:
        # --- query 1: cost by quality_profile ---
        rows = conn.execute(
            text(
                """
                SELECT
                    quality_profile,
                    COUNT(DISTINCT session_id) AS sessions,
                    ROUND(
                        SUM(cost_usd::numeric) / NULLIF(COUNT(DISTINCT session_id), 0),
                        4
                    ) AS avg_cost_per_session_usd
                FROM usage_logs
                WHERE session_id IS NOT NULL
                GROUP BY quality_profile
                ORDER BY avg_cost_per_session_usd DESC
                """
            )
        ).fetchall()
        results["by_quality_profile"] = [
            {
                "quality_profile": r[0],
                "sessions": r[1],
                "avg_cost_per_session_usd": float(r[2] or 0),
            }
            for r in rows
        ]

        # --- query 2: cost by provider/operation ---
        rows = conn.execute(
            text(
                """
                SELECT
                    provider,
                    operation,
                    ROUND(AVG(cost_usd::numeric), 6) AS avg_cost_usd,
                    ROUND(AVG(latency_ms)) AS avg_latency_ms,
                    COUNT(*) AS call_count
                FROM usage_logs
                GROUP BY provider, operation
                ORDER BY avg_cost_usd DESC
                """
            )
        ).fetchall()
        results["by_provider_operation"] = [
            {
                "provider": r[0],
                "operation": r[1],
                "avg_cost_usd": float(r[2] or 0),
                "avg_latency_ms": int(r[3] or 0),
                "call_count": r[4],
            }
            for r in rows
        ]

        # --- query 3: Anthropic prompt cache stats ---
        rows = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_calls,
                    ROUND(
                        100.0 * SUM(CASE WHEN cached THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
                        1
                    ) AS cache_hit_pct
                FROM usage_logs
                WHERE provider = 'anthropic'
                """
            )
        ).fetchone()
        results["anthropic_cache"] = {
            "total_calls": rows[0] if rows else 0,
            "cache_hit_pct": float(rows[1] or 0) if rows else 0.0,
            "note": (
                "Rubric prefix (~4K tokens) is cached on first call per session. "
                "Cache hit eliminates ~70% of input token cost for scoring."
            ),
        }

    return results


def main() -> None:
    """Query usage_logs and print cost profile JSON to stdout."""
    print(
        "WARNING: output contains real aggregated data. Do NOT commit to results/.",
        file=sys.stderr,
    )
    results = run_queries()
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
