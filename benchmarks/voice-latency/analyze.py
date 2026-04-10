"""Voice pipeline latency analysis -- queries real session_metrics table.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python benchmarks/voice-latency/analyze.py [--days 30]

WARNING: Output contains aggregated data from real sessions.
         Do NOT commit output. Use results/example.json as the reference.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def _get_database_url() -> str:
    """Read DATABASE_URL from environment, swapping asyncpg driver for sync psycopg2."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL env var not set", file=sys.stderr)
        print(
            "Usage: DATABASE_URL=postgresql://... python benchmarks/voice-latency/analyze.py",
            file=sys.stderr,
        )
        sys.exit(1)
    if "asyncpg" in url:
        url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    return url


def run_analysis(days: int) -> dict[str, object]:
    """Query session_metrics for voice latency percentiles over the last N days."""
    from sqlalchemy import create_engine, text  # noqa: PLC0415

    engine = create_engine(_get_database_url())
    kpi_target = 1000

    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_turns,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY e2e_latency_ms) AS e2e_p50,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY e2e_latency_ms) AS e2e_p95,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY e2e_latency_ms) AS e2e_p99,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY stt_latency_ms)  AS stt_p50,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY stt_latency_ms)  AS stt_p95,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY llm_ttft_ms)     AS llm_ttft_p50,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY llm_ttft_ms)     AS llm_ttft_p95,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY tts_latency_ms)  AS tts_p50,
                    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY tts_latency_ms)  AS tts_p95
                FROM session_metrics
                WHERE e2e_latency_ms IS NOT NULL
                  AND created_at > NOW() - INTERVAL :days_interval
                """
            ),
            {"days_interval": f"{days} days"},
        ).fetchone()

    if row is None or row[0] == 0:
        return {"error": "No data found for the specified time window."}

    e2e_p95 = int(row[2]) if row[2] is not None else None
    kpi_pass = e2e_p95 is not None and e2e_p95 < kpi_target

    return {
        "measurement_window": f"{days} days",
        "total_turns_analyzed": int(row[0]),
        "e2e_latency_ms": {
            "p50": int(row[1]) if row[1] is not None else None,
            "p95": e2e_p95,
            "p99": int(row[3]) if row[3] is not None else None,
        },
        "stt_latency_ms": {
            "p50": int(row[4]) if row[4] is not None else None,
            "p95": int(row[5]) if row[5] is not None else None,
        },
        "llm_ttft_ms": {
            "p50": int(row[6]) if row[6] is not None else None,
            "p95": int(row[7]) if row[7] is not None else None,
        },
        "tts_latency_ms": {
            "p50": int(row[8]) if row[8] is not None else None,
            "p95": int(row[9]) if row[9] is not None else None,
        },
        "kpi_target_e2e_p95_ms": kpi_target,
        "kpi_status": "PASS" if kpi_pass else "FAIL",
    }


def main() -> None:
    """Analyze voice latency from session_metrics and print JSON to stdout."""
    parser = argparse.ArgumentParser(description="Voice latency analysis from session_metrics")
    parser.add_argument("--days", type=int, default=30, help="Analysis window in days (default: 30)")
    args = parser.parse_args()

    print(
        "WARNING: output contains real session data. Do NOT commit to results/.",
        file=sys.stderr,
    )
    result = run_analysis(args.days)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
