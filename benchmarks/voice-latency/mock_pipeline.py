"""Mock voice pipeline latency profiler.

Simulates realistic STT -> LLM TTFT -> TTS first-byte latency distributions
using timing models based on known provider SLAs. No real API calls.

Usage:
    python benchmarks/voice-latency/mock_pipeline.py [--turns 100] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import random
from typing import Any


def _normal_clamp(mu: float, sigma: float, lo: float, hi: float, rng: random.Random) -> float:
    """Sample from a normal distribution clamped to [lo, hi]."""
    while True:
        v = rng.gauss(mu, sigma)
        if lo <= v <= hi:
            return v


def simulate_turns(
    n: int,
    rng: random.Random,
) -> list[dict[str, float]]:
    """Simulate N voice pipeline turns and return per-turn latency dicts."""
    turns = []
    for _ in range(n):
        stt = _normal_clamp(180, 40, 80, 400, rng)
        llm_ttft = _normal_clamp(310, 80, 120, 700, rng)
        tts = _normal_clamp(390, 90, 150, 750, rng)
        # Naive: purely sequential
        e2e_naive = stt + llm_ttft + tts
        # Optimized: TTS starts after first LLM sentence (~60% of LLM TTFT)
        # This reduces E2E because TTS and remaining LLM generation overlap
        first_sentence_ttft = llm_ttft * 0.6
        e2e_opt = stt + first_sentence_ttft + tts
        turns.append({
            "stt_ms": stt,
            "llm_ttft_ms": llm_ttft,
            "tts_ms": tts,
            "e2e_naive_ms": e2e_naive,
            "e2e_optimized_ms": e2e_opt,
        })
    return turns


def percentile(values: list[float], p: int) -> float:
    """Compute the p-th percentile of a sorted list of values."""
    sorted_v = sorted(values)
    idx = int(len(sorted_v) * p / 100)
    idx = min(idx, len(sorted_v) - 1)
    return round(sorted_v[idx])


def compute_stats(turns: list[dict[str, float]]) -> dict[str, Any]:
    """Compute p50/p95/p99 statistics across simulated turns."""
    stt = [t["stt_ms"] for t in turns]
    llm = [t["llm_ttft_ms"] for t in turns]
    tts = [t["tts_ms"] for t in turns]
    e2e_naive = [t["e2e_naive_ms"] for t in turns]
    e2e_opt = [t["e2e_optimized_ms"] for t in turns]

    kpi_target = 1000
    e2e_p95 = percentile(e2e_opt, 95)

    return {
        "turns_simulated": len(turns),
        "naive_pipeline": {
            "e2e_p50": percentile(e2e_naive, 50),
            "e2e_p95": percentile(e2e_naive, 95),
            "e2e_p99": percentile(e2e_naive, 99),
        },
        "optimized_pipeline": {
            "description": "Sentence-streaming: TTS starts after first LLM sentence (~60% TTFT)",
            "e2e_p50": percentile(e2e_opt, 50),
            "e2e_p95": e2e_p95,
            "e2e_p99": percentile(e2e_opt, 99),
        },
        "stt_ms": {
            "p50": percentile(stt, 50),
            "p95": percentile(stt, 95),
        },
        "llm_ttft_ms": {
            "p50": percentile(llm, 50),
            "p95": percentile(llm, 95),
        },
        "tts_ms": {
            "p50": percentile(tts, 50),
            "p95": percentile(tts, 95),
        },
        "kpi_target_e2e_p95_ms": kpi_target,
        "kpi_status": "PASS" if e2e_p95 < kpi_target else "FAIL",
    }


def print_table(stats: dict[str, Any]) -> None:
    """Print a formatted results table to stdout."""
    sep = "-" * 60
    opt = stats["optimized_pipeline"]
    naive = stats["naive_pipeline"]
    stt = stats["stt_ms"]
    llm = stats["llm_ttft_ms"]
    tts = stats["tts_ms"]

    lines = [
        "",
        "InterviewCraft Voice Pipeline — Mock Latency Profile",
        sep,
        f"  Turns simulated:  {stats['turns_simulated']}",
        "  Model:            STT=N(180,40) LLM=N(310,80) TTS=N(390,90) [ms]",
        "",
        "  Metric               p50      p95      p99",
        f"  E2E (naive)       {naive['e2e_p50']:>6}ms  {naive['e2e_p95']:>6}ms  {naive['e2e_p99']:>6}ms",
        f"  E2E (optimized)   {opt['e2e_p50']:>6}ms  {opt['e2e_p95']:>6}ms  {opt['e2e_p99']:>6}ms  <- production",
        f"  STT               {stt['p50']:>6}ms  {stt['p95']:>6}ms",
        f"  LLM TTFT          {llm['p50']:>6}ms  {llm['p95']:>6}ms",
        f"  TTS first byte    {tts['p50']:>6}ms  {tts['p95']:>6}ms",
        "",
        f"  KPI target:       p95 < {stats['kpi_target_e2e_p95_ms']}ms",
        f"  KPI status:       {stats['kpi_status']}  (p95={opt['e2e_p95']}ms)",
        "",
        "  Sentence-streaming reduces E2E by dispatching TTS after the first",
        "  LLM sentence instead of waiting for the full response.",
        sep,
        "",
    ]
    for line in lines:
        print(line)


def main() -> None:
    """Run the mock pipeline simulation and print results."""
    parser = argparse.ArgumentParser(description="Mock voice pipeline latency profiler")
    parser.add_argument("--turns", type=int, default=100, help="Number of turns to simulate (default: 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--json", dest="json_out", action="store_true", help="Output JSON instead of table")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    turns = simulate_turns(args.turns, rng)
    stats = compute_stats(turns)

    if args.json_out:
        print(json.dumps(stats, indent=2))
    else:
        print_table(stats)


if __name__ == "__main__":
    main()
