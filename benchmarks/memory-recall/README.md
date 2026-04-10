# Memory Recall Benchmark

Measures how accurately the InterviewCraft memory system recalls facts about returning candidates.

## What it tests

Five synthetic user profiles (A–E) covering distinct scenarios:
| Profile | Sessions | Scenario |
|---------|----------|----------|
| A | 8 | Rich history — 3 weak skills with mistakes, 3 stories |
| B | 25 | Power user — 2 coaching insights, 2 stories, goal context |
| C | 3 | Sparse (bootstrap-only) — no stories, no recurring mistakes |
| D | 6 | Flat scores (all near 50), no career context |
| E | 15 | Many recurring mistakes, strong comm patterns |

40 questions across 6 categories: `direct`, `numerical`, `story`, `communication`, `multi_fact`, `negative`.

Scoring per question: `2`=correct · `1`=partial · `0`=miss · `-1`=hallucination

## Latest results (2026-04-10)

| Metric | Result |
|--------|--------|
| Recall rate (score=2) | 95.0% |
| Partial rate (score=1) | 2.5% |
| Miss rate (score=0) | 2.5% |
| Hallucination rate (score=-1) | 0.0% |
| Cost | $0.019 (40 × Haiku) |
| Model | claude-haiku-4-5 |

## How to reproduce

```bash
export ANTHROPIC_API_KEY=...
python benchmarks/memory-recall/run.py --confirm
```

Cost estimate is printed before any calls. Pass `--confirm` to proceed (~$0.019).

## Architecture note

The benchmark exercises `app.services.memory.loader._format_memory_block()` directly — the same
function called during every real voice session. Results reflect real production memory formatting
quality.

All profile data is purpose-built for benchmark coverage — not drawn from production sessions.
