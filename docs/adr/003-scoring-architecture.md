# ADR-003: Scoring Architecture

**Status:** Accepted
**Date:** 2026-02-25
**Authors:** Lead Dev + Architect

---

## Problem

How do we reliably score an interview answer at low cost, without hallucinated evidence, and with stable results across runs?

Four sub-problems:

1. **Evidence integrity** — LLMs hallucinate quotes. We need ground truth.
2. **Cost** — Scoring N segments × 3 tasks (score + diff + memory) = 3N API calls at naive implementation.
3. **Stability** — Same answer scored twice should land within ±8 points. Quality is meaningless otherwise.
4. **Parse reliability** — LLM JSON output can fail. What's the fallback?

---

## Options Considered

### Option A: One call per task (separate score, diff, memory)

- 3 API calls per segment
- Simple to debug
- Highest latency + cost (3× vs batched)
- Rejected: violates DoD cost targets (~$0.65/session Quality)

### Option B: One batched call (score + diff + memory hints)

- Single Anthropic tool_use call per segment
- All three outputs in one JSON blob
- Risk: if one part fails, all fail
- Mitigation: JSON retry with repair prompt (up to 2 retries)
- **Selected** ✅

### Option C: Streaming score (real-time feedback during session)

- Score each answer the moment the user finishes speaking
- User gets lint results immediately, before next question
- Latency concern: ~3-8s scoring call interrupts interview flow
- Rejected for MVP; may revisit as background task in Week 7-8

### Option D: Holistic session scoring (score entire transcript once)

- Single call for entire session
- Loses per-segment granularity needed for Rewind (Week 5-6)
- Cannot link rules to specific timestamps
- Rejected: breaks evidence span architecture

---

## Decision

**One batched Anthropic tool_use call per Q&A segment.**

### Evidence architecture (critical)

LLMs hallucinate quotes. This is not acceptable for a tool that claims evidence-based feedback.

**Solution**: LLM returns `{start_ms, end_ms}` span references only. Server extracts the actual quote from the `transcript_words` table (TTL 14 days) by finding words whose timestamps fall within the span (±200ms tolerance).

```
LLM response: {evidence: {start_ms: 102000, end_ms: 105000}}
Server lookup: SELECT word FROM transcript_words
               WHERE session_id=X AND start_ms BETWEEN 101800 AND 105200
               ORDER BY start_ms
→ "improved performance" (actual spoken words)
```

This makes it impossible for the LLM to fabricate a quote that doesn't exist in the transcript.

### Prompt caching

The rubric (15 rules + format instructions + level expectations) is ~1300 tokens and never changes. Sending it as an Anthropic `cache_control: ephemeral` block:

| Token type | Price | After cache |
|---|---|---|
| Input (uncached) | $3.00/MTok (Sonnet) | — |
| Input (cached read) | $0.30/MTok | 90% off ✅ |
| Cache write | $3.75/MTok | One-time only |

**Expected cache hit rate**: >80% (same rubric used for all scoring within a 5-minute window).

Tracked in `usage_logs.cached` and surfaced in `/admin/metrics` as "Prompt cache hit rate".

### Model routing

Per quality profile, per spec Section 2.3:

| Profile | Scoring model | Diff model | Expected cost/session |
|---|---|---|---|
| Quality | Sonnet 4.6 | Sonnet 4.6 | ~$0.65 |
| Balanced | Haiku 4.5 | Haiku 4.5 | ~$0.35 |
| Budget | Haiku 4.5 | Haiku 4.5 | ~$0.15 |

Note: Scoring rubric was calibrated on Sonnet. Haiku variance ≈ ±6 vs ±4 (acceptable, within DoD < 8 threshold).

### JSON reliability

Tool_use is more reliable than text-mode JSON parsing (no regex, no `json.loads` on arbitrary text). But even tool_use can fail.

```
Max retries: 2
On retry: append "PREVIOUS ATTEMPT FAILED — return ONLY the structured_output tool call"
Track: json_parse_fail_rate in usage_logs/metrics (target < 5%)
Track: repair_success_rate (how often retry succeeds, target > 80%)
Alert if fail_rate > 5% (metrics dashboard Week 9-10)
```

---

## Tradeoffs Accepted

| Tradeoff | Rationale |
|---|---|
| Single batched call means one failure kills all outputs | Mitigated by retry. Partial success (score without diff) not worth the complexity. |
| Cache warm-up cost | First call per rubric version pays cache write. Amortized across 100s of sessions, negligible. |
| Haiku for Balanced/Budget has higher variance | Measured at ±6 vs ±4. Still within DoD < 8 threshold. Acceptable for daily practice. |
| Scoring is client-triggered (not automatic) | User sees a "Score Session" button instead of instant results. Avoids blocking session end on a 3-8s scoring call. |
| transcript_words TTL 14 days | Quote extraction only needed for active sessions. Old sessions lose exact quote but retain {start_ms, end_ms} for timestamp links. |

---

## Implementation

```
backend/app/services/scoring/rubric.py  — 15 rules + RUBRIC_PROMPT_PREFIX (cached)
backend/app/services/scoring/scorer.py  — Scorer class, score_segment(), _fill_evidence_quotes()
backend/app/api/v1/scoring.py           — POST /sessions/{id}/score, GET /sessions/{id}/scores
backend/tests/scoring/golden_answers.json — 10 test cases (weak/mid/strong)
backend/tests/scoring/test_golden_answers.py — unit + integration + nightly suites
```

---

## Measured Results

*To be filled after first live scoring session:*

- json_parse_fail_rate: TBD (target < 5%)
- repair_success_rate: TBD (target > 80%)
- cache_hit_rate: TBD (target > 70%)
- scoring_latency_p50: TBD (expected 3-8s, not on critical voice path)
- golden_test_variance: TBD (target < 8 per answer)
- cost_per_segment_balanced: TBD (expected ~$0.04-0.08)
