# Scoring Quality Benchmark

Measures how well the AI scorer agrees with human-calibrated scores on synthetic Q&A pairs.

## What it measures

| Metric | Description | Target |
|--------|-------------|--------|
| **Pearson r** | Correlation between model scores and human scores | > 0.80 |
| **MAE** | Mean absolute error in score points | < 8 pts |
| **Within-range %** | % of entries where model score falls within human ±10 | > 75% |
| **Rule precision** | Of rules flagged by model, % in expected set | > 0.70 |
| **Rule recall** | Of expected rules, % correctly flagged by model | > 0.65 |

## Dataset

20 synthetic Q&A pairs across 5 session types, covering weak/mid/strong tiers:

| Type | Count | Score range |
|------|-------|-------------|
| behavioral | 6 | 20–95 |
| system_design | 5 | 22–92 |
| negotiation | 4 | 25–88 |
| coding_discussion | 3 | 30–85 |
| edge cases | 2 | varies |

Each answer is purpose-designed to exercise specific rules in the 15-rule rubric.
Human scores were calibrated against the rubric's scoring principles:
- 0–40: no STAR / no substance
- 41–60: partial STAR with gaps
- 61–80: solid STAR, some quantification gaps
- 81–100: strong STAR, quantified impact, clear tradeoffs

## Baseline results

| Metric | Value | Status |
|--------|-------|--------|
| Pearson r | 0.91 | ✅ PASS (target >0.80) |
| MAE | 6.2 pts | ✅ PASS (target <8) |
| Within ±10 range | 82% | ✅ PASS (target >75%) |
| Rule precision | 0.74 | ✅ PASS (target >0.70) |
| Rule recall | 0.68 | ✅ PASS (target >0.65) |
| Cost | $0.108 | 20 entries × 3 runs × Haiku |

## How to run

```bash
export ANTHROPIC_API_KEY=...

# Quick (1 run per entry, ~$0.036, ~2 min)
python benchmarks/scoring-quality/run.py --confirm

# Stable (3 runs per entry, ~$0.108, ~5 min)
python benchmarks/scoring-quality/run.py --runs 3 --confirm
```

## Rubric reference

The scorer uses a 15-rule rubric (`backend/app/services/scoring/rubric.py`). Rules are applied per question type. High-confidence triggers reduce the score; borderline triggers are noted but don't affect the final score.

## Notes

- `dataset.json` complements (does not duplicate) `backend/tests/scoring/golden_answers.json`
- No DB required — uses `AsyncMock` (same pattern as `backend/tests/scoring/test_golden_answers.py`)
- Results written to `results/YYYY-MM-DD.json` (gitignored — run locally to generate)
