# InterviewCraft — Benchmarks

Reproducible evaluation suite for all AI subsystems. Published for transparency.

> **All committed result files contain synthetic or example data only.**
> No real user data, no production DB exports.
> Run the scripts locally against your own infrastructure for real numbers.

## Quick summary

| Benchmark | What it measures | Latest result | Cost/run | Needs DB | Needs key |
|-----------|-----------------|---------------|----------|----------|-----------|
| [memory-recall/](memory-recall/) | Memory recall accuracy (5 profiles, 40 Q) | 95.0% recall · 0% hallucination | ~$0.019 | No | Anthropic |
| [cost-profile/](cost-profile/) | API cost per session by provider | ~$0.031/session (balanced) | Free | Yes | No |
| [voice-latency/](voice-latency/) | STT + LLM TTFT + TTS first-byte | E2E p95 940ms (KPI: <1000ms) | Free (mock) | Optional | No |
| [scoring-quality/](scoring-quality/) | Scorer vs. human-calibrated scores | Pearson r=0.91 · MAE=6.2 | ~$0.04 | No | Anthropic |

## Design principles

1. **Committed results are synthetic.** Scripts that query real infrastructure warn against committing their output.
2. **`--confirm` required** before any paid API calls — estimated cost is printed first.
3. **Model tier convention** (same as production):
   - `claude-haiku-4-5` — scoring evals, memory recall
   - `claude-sonnet-4-6` — voice LLM, complex tasks
4. **Offline tools require no credentials** — `mock_pipeline.py` and `dataset.json` work without API keys or DB.

## Running all benchmarks

```bash
# From repo root
export ANTHROPIC_API_KEY=...

# Memory recall (~$0.019, ~2 min)
python benchmarks/memory-recall/run.py --confirm

# Scoring quality (~$0.04, ~3 min with --runs 1)
python benchmarks/scoring-quality/run.py --confirm

# Voice latency — offline mock (free, instant)
python benchmarks/voice-latency/mock_pipeline.py

# Cost profile — requires live DB
DATABASE_URL=postgresql+asyncpg://user:pass@host/db python benchmarks/cost-profile/query.py

# Voice latency — real data, requires live DB
DATABASE_URL=postgresql+asyncpg://user:pass@host/db python benchmarks/voice-latency/analyze.py
```
