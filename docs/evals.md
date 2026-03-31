# InterviewCraft — Scoring Evaluation Methodology

> How we measure scoring quality, detect regressions, and calibrate the rubric.

---

## Why Evals Matter

InterviewCraft's moat is accurate, consistent scoring. If the rubric drifts between
Claude versions (or between runs of the same version), users lose trust in deltas
("did I actually improve, or did the model just score differently today?").

**DoD KPI:** Scoring variance < 8 points across 5 runs of the same answer.

---

## The Rubric (15 Rules)

Defined in `backend/app/services/scoring/rubric.py`. Each rule has:
- `id`: unique slug (e.g., `star_structure`, `tradeoff_analysis`)
- `name`: human-readable label
- `description`: what the evaluator checks
- `category`: `structure | depth | communication | seniority_signal`
- `applies_to`: list of session types this rule fires on
- `impact`: 1–10 (how much the rule affects overall score)
- `fix`: one-line actionable advice shown in the Lint Card

All 15 rules are fed to Claude as a **cached prefix** (Anthropic prompt caching).
This means the rubric instructions are fixed in the cache — Claude sees exactly
the same rubric text every time, which is the single biggest driver of consistency.

---

## Golden Answer Test Suite

Location: `backend/tests/scoring/golden_answers.json`

Schema:
```json
{
  "id": "behavioral_star_strong_001",
  "question": "Tell me about a time you led a complex technical project.",
  "answer": "...",
  "expected_rules_triggered": ["star_structure", "result_quantification"],
  "expected_rules_not_triggered": ["vague_outcome"],
  "expected_score_range": [72, 88],
  "session_type": "behavioral",
  "notes": "Strong STAR with quantified result. Should pass L5."
}
```

### Lite suite (CI)
- 10 test cases × 3 runs each = 30 scoring calls per CI run
- Asserts:
  1. Score within `expected_score_range` in all 3 runs
  2. Variance (max - min) ≤ 8 across 3 runs
  3. All `expected_rules_triggered` appear in ≥ 2/3 runs
  4. No `expected_rules_not_triggered` appear in > 1/3 runs

### Full suite (nightly/release gate)
- 30 test cases × 5 runs each = 150 scoring calls
- Stricter: variance ≤ 6 across 5 runs
- Includes edge cases: very short answers, very long answers, non-native English

### Running the suites
```bash
# Lite suite (uses real Anthropic API — ~$0.15 per run)
pytest tests/scoring/test_golden_answers.py -m lite -v

# Full suite (nightly)
pytest tests/scoring/test_golden_answers.py -m nightly -v

# Skip scoring tests (no API key)
pytest -m "not integration and not nightly" -q
```

---

## Variance Tracking

Every run of the golden suite writes to `tests/scoring/variance_log.jsonl`:
```json
{"date": "2026-02-25", "model": "claude-sonnet-4-6", "test_id": "behavioral_star_strong_001",
 "scores": [78, 80, 77], "variance": 3, "passed": true}
```

Run `python scripts/variance_report.py` to get:
- Per-rule consistency (which rules fire most/least consistently)
- Per-category variance
- Trend over time (regression detection)

---

## Calibration Process

When rubric rules change:

1. Update `rubric.py` with new/modified rules.
2. Run full golden suite: `pytest -m nightly`
3. If variance > 8 on any test case: adjust the rule `description` to be more specific.
4. Target: 30/30 test cases within variance ≤ 6.
5. Add new test case for the changed rule (min 1 strong + 1 weak example).
6. Log calibration run in `docs/devlog/` with model version + variance results.

**Important:** Calibration is model-specific. If Claude Sonnet version changes,
re-run the full suite before deploying. Score drift between Claude versions is expected
and must be detected before users notice.

---

## Evidence Quality

Beyond score consistency, we validate evidence extraction:

- **Evidence type:** spans (`{start_ms, end_ms}`) — server extracts quotes, never LLM.
- **Span validity:** every span must reference an existing word in `transcript_words`.
- **Quote accuracy:** server-extracted quote must contain the rule keyword.

Test: `tests/scoring/test_evidence.py` — verifies span → quote extraction on synthetic transcripts.

---

## Scoring Variance by Category (baseline targets)

| Category | Target max variance | Hardest rules |
|---|---|---|
| structure | ≤ 5 | `star_structure` (clear markers) |
| depth | ≤ 8 | `tradeoff_analysis` (subjective) |
| communication | ≤ 5 | `conciseness` (word count signal) |
| seniority_signal | ≤ 10 | `ownership_language` (LLM judgment-heavy) |

`seniority_signal` has highest variance by design — it requires holistic judgment.
It also carries the highest impact weight to compensate.

---

## What We Don't Eval (and why)

| Item | Reason not evaled |
|---|---|
| Diff quality (3 versions) | Too subjective; use user ratings instead (Phase 2) |
| Story detection accuracy | Need labeled dataset from real sessions |
| Negotiation scoring | Calibration in progress (Week 7-8) |
| Voice latency | Measured live via session_metrics, not test suite |
