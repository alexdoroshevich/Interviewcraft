# ADR-008: Scoring Stability Architecture

**Status:** Accepted
**Date:** 2026-02-25

---

## Problem

LLM-based scoring is inherently stochastic. The same answer can score 72 one run
and 65 the next. If a user's score changes because the model changed, not because
their answer improved, the delta is meaningless. Trust collapses.

---

## Decision

Use four complementary techniques to reduce scoring variance below 8 points across runs:

### 1. Anthropic Prompt Caching (primary)

The 15-rule rubric + output format instructions (~1300 tokens) are sent as a
`cache_control: ephemeral` prefix in every scoring call.

**Why this works:** When the prefix is cached, Claude processes it once and reuses
the same internal state. Variance from prompt re-parsing is eliminated. Cache hit rate
target: > 70% (monitored in admin metrics).

**Cost benefit:** Cached input tokens cost 10% of normal input tokens. At 1300 tokens
per call, caching saves ~$0.035/session on the Balanced profile — 10% of session cost.

### 2. Fixed Temperature (temperature = 0)

All scoring calls use `temperature=0` (deterministic sampling).

**Why this matters:** Even with identical prompts, non-zero temperature introduces
sampling randomness. At temperature=0, given the same cached KV state, Claude
produces identical output.

**Tradeoff:** Diff generation uses temperature=0.3 (slightly creative rewrites).
Voice LLM uses temperature=0.7 (more natural conversation). Scoring is the only
component that must be deterministic.

### 3. Structured Output Format (JSON schema enforced)

Scoring response must match a fixed JSON schema:
```json
{
  "overall_score": int,
  "category_scores": { "structure": int, "depth": int, "communication": int, "seniority_signal": int },
  "rules_triggered": [{ "rule": str, "confidence": "strong|weak", "evidence": {...}, "fix": str }],
  "level_assessment": { "l4_pass": bool, "l5_pass": bool, "l6_pass": bool, "gaps": [...] }
}
```

**Why this matters:** Freeform prose → score extraction introduces parsing variance.
A fixed schema means the model fills slots, not narrates — structurally more consistent.

**JSON repair:** If parsing fails, one repair attempt with `"Fix this JSON: <response>"`.
Tracked as `json_parse_fail_rate`. Target: < 5%. Repair success target: > 80%.

### 4. Golden Answer Regression Tests

30 test cases × 5 runs each, nightly. Assert:
- Every score within expected range
- Variance (max - min) ≤ 6 across 5 runs
- Rule triggers stable across runs (≥ 4/5 runs for expected rules)

CI runs 10 × 3 lite suite on every PR. If variance > 8 on any case, PR blocked.

---

## Options Considered

| Option | Verdict |
|---|---|
| Re-run scoring 3x, take median | Too expensive (3× API cost per answer) |
| Fine-tune a smaller model on golden answers | Phase 2 — requires 1000+ labeled examples |
| Use structured outputs API (JSON mode) | Anthropic doesn't have JSON mode → manual schema enforcement |
| Lower temperature only | Not sufficient alone — caching is the primary lever |

---

## Measured Results (calibration run 2026-02-24)

Model: `claude-sonnet-4-6`
Suite: 10 cases × 3 runs (lite)

| Category | Avg variance | Max variance |
|---|---|---|
| structure | 3.1 | 5 |
| depth | 5.4 | 8 |
| communication | 2.8 | 4 |
| seniority_signal | 6.2 | 9 |
| **overall_score** | **4.1** | **7** |

Overall variance 4.1 average, 7 max — within the < 8 DoD target.

`seniority_signal` is the highest-variance category (as expected — most LLM-judgment-heavy).
Mitigation: `seniority_signal` rules have the most specific `description` text.

---

## Tradeoffs

| Tradeoff | Rationale |
|---|---|
| temperature=0 → less creative scoring feedback | Acceptable. Fixes are in the rubric, not the prose. |
| JSON schema constrains scoring flexibility | Intentional — schema IS the rubric contract. |
| Nightly suite costs ~$0.50/run | Cheap insurance against silent regressions. |
| Cache eviction causes variance spike | Monitored. Backend restart re-warms in < 60s. |
