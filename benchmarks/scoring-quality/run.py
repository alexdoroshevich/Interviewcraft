"""Scoring quality benchmark for the InterviewCraft Scorer.

Measures how closely the automated scorer agrees with human-annotated scores
on a fixed dataset of 20 Q&A pairs across behavioral, system_design,
negotiation, and coding_discussion question types.

Metrics computed:
  - Pearson r       (correlation with human scores)
  - MAE             (mean absolute error vs human scores)
  - within_range_pct (% of predictions inside expected_score_range)
  - Rule precision  (of rules model triggered, fraction are expected)
  - Rule recall     (of expected rules, fraction model triggered)

Run from repo root:
    python benchmarks/scoring-quality/run.py --confirm

Omit --confirm to print cost estimate only (no API calls).
Output is written to benchmarks/scoring-quality/results/YYYY-MM-DD.json.

WARNING: Never commit the generated dated file — it may contain model outputs
that could be used to reverse-engineer scoring internals. Only example.json
(synthetic data) is safe to commit.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import structlog

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(REPO_ROOT / ".env", override=False)
except ImportError:
    pass

logging.basicConfig(format="%(message)s", level=logging.INFO, stream=sys.stdout)
structlog.configure(
    processors=[structlog.processors.KeyValueRenderer(key_order=["event"], drop_missing=True)],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
log = structlog.get_logger("scoring_benchmark")

DATASET_PATH = Path(__file__).parent / "dataset.json"
RESULTS_DIR = Path(__file__).parent / "results"

# Approximate cost per entry at Haiku balanced profile (input ~1500 tokens, output ~200 tokens)
_COST_PER_ENTRY_USD = 0.0008
_PROFILE = "balanced"  # Use Haiku — same model used in production balanced profile


# ── Mock DB helper ────────────────────────────────────────────────────────────


def _mock_db() -> Any:
    """Return a minimal AsyncSession mock that satisfies the Scorer's DB calls.

    The Scorer calls db.execute() for:
      1. transcript_words lookup (for quote extraction) → returns empty list
      2. usage_logs insert (db.add + db.commit) → no-op
    """
    db = AsyncMock()
    words_result = MagicMock()
    words_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=words_result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


# ── Statistics helpers ────────────────────────────────────────────────────────


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    """Compute Pearson correlation coefficient."""
    n = len(xs)
    if n < 2:
        return 0.0
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return round(num / den, 4) if den > 0 else 0.0


def _mae(predictions: list[float], targets: list[float]) -> float:
    """Compute mean absolute error."""
    n = len(predictions)
    if n == 0:
        return 0.0
    return round(sum(abs(p - t) for p, t in zip(predictions, targets)) / n, 2)


def _within_range_pct(
    predictions: list[float], ranges: list[tuple[int, int]]
) -> float:
    """Percentage of predictions that fall within their expected score range."""
    if not predictions:
        return 0.0
    hits = sum(
        1 for p, (lo, hi) in zip(predictions, ranges) if lo <= p <= hi
    )
    return round(100.0 * hits / len(predictions), 1)


def _rule_metrics(
    triggered_lists: list[list[str]], expected_lists: list[list[str]]
) -> dict[str, float]:
    """Aggregate rule precision and recall across all entries."""
    tp = fp = fn = 0
    for triggered, expected in zip(triggered_lists, expected_lists):
        triggered_set = set(triggered)
        expected_set = set(expected)
        tp += len(triggered_set & expected_set)
        fp += len(triggered_set - expected_set)
        fn += len(expected_set - triggered_set)
    precision = round(tp / (tp + fp), 3) if (tp + fp) > 0 else 1.0
    recall = round(tp / (tp + fn), 3) if (tp + fn) > 0 else 1.0
    return {"precision": precision, "recall": recall, "tp": tp, "fp": fp, "fn": fn}


# ── Benchmark runner ──────────────────────────────────────────────────────────


async def run_benchmark(api_key: str) -> dict[str, Any]:
    """Score all dataset entries and compute aggregate metrics."""
    from app.services.scoring.scorer import Scorer

    dataset = json.loads(DATASET_PATH.read_text())
    scorer = Scorer(api_key=api_key, quality_profile=_PROFILE)

    human_scores: list[float] = []
    model_scores: list[float] = []
    score_ranges: list[tuple[int, int]] = []
    triggered_rule_lists: list[list[str]] = []
    expected_rule_lists: list[list[str]] = []
    per_entry_results: list[dict[str, Any]] = []

    total_cost = 0.0
    total_input_tokens = 0
    total_output_tokens = 0

    for i, entry in enumerate(dataset, 1):
        entry_id = entry["id"]
        log.info("scoring.entry", index=i, total=len(dataset), id=entry_id)

        answer_transcript = [
            {"role": "assistant", "content": entry["question"], "ts_ms": 0},
            {"role": "user", "content": entry["answer"], "ts_ms": 1000},
        ]

        try:
            result = await scorer.score_segment(
                session_id=uuid.uuid4(),
                segment_index=0,
                question=entry["question"],
                answer_transcript=answer_transcript,
                question_type=entry["question_type"],
                target_level="L5",
                db=_mock_db(),
                user_id=uuid.uuid4(),
            )
        except Exception as exc:
            log.warning("scoring.entry_failed", id=entry_id, error=str(exc))
            per_entry_results.append(
                {
                    "id": entry_id,
                    "error": str(exc),
                    "human_score": entry["human_score"],
                }
            )
            continue

        triggered_ids = [r.get("rule_id", r.get("id", "")) for r in result.rules_triggered]
        cost_usd = result.input_tokens * 0.00000025 + result.output_tokens * 0.00000125

        human_scores.append(entry["human_score"])
        model_scores.append(result.overall_score)
        score_ranges.append(tuple(entry["expected_score_range"]))  # type: ignore[arg-type]
        triggered_rule_lists.append(triggered_ids)
        expected_rule_lists.append(entry.get("expected_rules", []))
        total_cost += cost_usd
        total_input_tokens += result.input_tokens
        total_output_tokens += result.output_tokens

        per_entry_results.append(
            {
                "id": entry_id,
                "question_type": entry["question_type"],
                "tier": entry.get("tier", ""),
                "human_score": entry["human_score"],
                "model_score": result.overall_score,
                "expected_range": entry["expected_score_range"],
                "in_range": entry["expected_score_range"][0]
                <= result.overall_score
                <= entry["expected_score_range"][1],
                "confidence": result.confidence,
                "rules_triggered": triggered_ids,
                "expected_rules": entry.get("expected_rules", []),
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "latency_ms": result.latency_ms,
                "retries_used": result.retries_used,
            }
        )

    pearson = _pearson_r(model_scores, human_scores)
    mae = _mae(model_scores, human_scores)
    within_range = _within_range_pct(model_scores, score_ranges)
    rule_stats = _rule_metrics(triggered_rule_lists, expected_rule_lists)

    # Break out by question type
    by_type: dict[str, dict[str, Any]] = {}
    for entry_result in per_entry_results:
        if "error" in entry_result:
            continue
        qtype = entry_result["question_type"]
        if qtype not in by_type:
            by_type[qtype] = {"human": [], "model": [], "ranges": []}
        by_type[qtype]["human"].append(entry_result["human_score"])
        by_type[qtype]["model"].append(entry_result["model_score"])
        by_type[qtype]["ranges"].append(entry_result["expected_range"])

    type_metrics = {}
    for qtype, data in by_type.items():
        type_metrics[qtype] = {
            "pearson_r": _pearson_r(data["model"], data["human"]),
            "mae": _mae(data["model"], data["human"]),
            "within_range_pct": _within_range_pct(data["model"], data["ranges"]),
            "n": len(data["human"]),
        }

    return {
        "date": str(date.today()),
        "model": scorer._scoring_model,
        "quality_profile": _PROFILE,
        "n_entries": len(human_scores),
        "pearson_r": pearson,
        "mae": mae,
        "within_range_pct": within_range,
        "rule_precision": rule_stats["precision"],
        "rule_recall": rule_stats["recall"],
        "rule_tp": rule_stats["tp"],
        "rule_fp": rule_stats["fp"],
        "rule_fn": rule_stats["fn"],
        "total_cost_usd": round(total_cost, 5),
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
        "by_type": type_metrics,
        "per_entry": per_entry_results,
        "kpis": {
            "pearson_r_target": 0.85,
            "pearson_r_pass": pearson >= 0.85,
            "mae_target": 10,
            "mae_pass": mae <= 10,
            "within_range_target": 75.0,
            "within_range_pass": within_range >= 75.0,
        },
    }


# ── CLI entrypoint ────────────────────────────────────────────────────────────


def main() -> None:
    """CLI entrypoint for the scoring quality benchmark."""
    parser = argparse.ArgumentParser(
        description="Run the InterviewCraft scoring quality benchmark."
    )
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Actually run API calls. Without this flag, only the cost estimate is printed.",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ANTHROPIC_API_KEY", ""),
        help="Anthropic API key (defaults to ANTHROPIC_API_KEY env var).",
    )
    args = parser.parse_args()

    dataset = json.loads(DATASET_PATH.read_text())
    n = len(dataset)
    estimated_cost = n * _COST_PER_ENTRY_USD

    print("Scoring quality benchmark")
    print(f"  Dataset:        {DATASET_PATH.name} ({n} entries)")
    print("  Model:          Haiku (balanced profile)")
    print(f"  Estimated cost: ~${estimated_cost:.4f} USD")
    print("  KPI targets:    Pearson r >= 0.85 | MAE <= 10 | within_range >= 75%")
    print()

    if not args.confirm:
        print("Dry run. Pass --confirm to execute.")
        return

    if not args.api_key:
        print("ERROR: ANTHROPIC_API_KEY not set and --api-key not provided.", file=sys.stderr)
        sys.exit(1)

    results = asyncio.run(run_benchmark(args.api_key))

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / f"{results['date']}.json"
    out_path.write_text(json.dumps(results, indent=2))

    kpis = results["kpis"]
    all_pass = all(
        [kpis["pearson_r_pass"], kpis["mae_pass"], kpis["within_range_pass"]]
    )

    print()
    print("=" * 50)
    print("RESULTS SUMMARY")
    print("=" * 50)
    print(f"  Pearson r:       {results['pearson_r']:.3f}  (target >= 0.85) {'PASS' if kpis['pearson_r_pass'] else 'FAIL'}")
    print(f"  MAE:             {results['mae']:.1f}    (target <= 10)   {'PASS' if kpis['mae_pass'] else 'FAIL'}")
    print(f"  Within range:    {results['within_range_pct']:.1f}%  (target >= 75%)  {'PASS' if kpis['within_range_pass'] else 'FAIL'}")
    print(f"  Rule precision:  {results['rule_precision']:.3f}")
    print(f"  Rule recall:     {results['rule_recall']:.3f}")
    print(f"  Total cost:      ${results['total_cost_usd']:.5f} USD")
    print(f"  Entries scored:  {results['n_entries']}/{n}")
    print()
    print("  By question type:")
    for qtype, m in results["by_type"].items():
        print(f"    {qtype:<22} r={m['pearson_r']:.2f}  MAE={m['mae']:.1f}  n={m['n']}")
    print()
    print(f"  Output:  {out_path}")
    print()
    print(f"  Overall: {'ALL KPIs PASS' if all_pass else 'ONE OR MORE KPIs FAILED'}")
    print()
    print(
        "WARNING: Do not commit the dated output file — it may expose model behaviour.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
