# Interviewcraft benchmark entry points

These scripts distinguish synthetic examples, offline simulations and optional real-model runs. No current recall, correlation, latency percentile, cache-hit or session-cost measurement is asserted by this README. Committed `results/example.json` files demonstrate output shape only. Previously listed numbers without reproducible run provenance have been removed.

| Entry | Scope | External dependency |
|---|---|---|
| [memory recall](memory-recall/README.md) | Synthetic-profile context formatting and model recall; not persisted two-session behavior | Paid Anthropic API, explicit --confirm |
| [scoring quality](scoring-quality/README.md) | Synthetic Q&A compared with author-assigned references | Paid Anthropic API, explicit --confirm |
| [voice latency](voice-latency/README.md) | Offline timing simulation or analysis of saved session metrics | No API for simulator; DB for recorded metrics |
| [cost profile](cost-profile/README.md) | Aggregate usage-log estimates | Existing DB; no provider calls by query script |

Run from repository root in the configured Python environment:

```sh
python benchmarks/voice-latency/mock_pipeline.py --turns 1000
# Owner-approved paid runs only:
python benchmarks/memory-recall/run.py --confirm
python benchmarks/scoring-quality/run.py --confirm
```

See [evaluation conditions](../docs/evals.md). Synthetic/estimated values do not demonstrate live providers, scoring accuracy or product adoption. No paid benchmark was run for this local review.
