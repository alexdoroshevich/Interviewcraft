# ADR-004: Rewind Segmentation

**Status:** Accepted
**Date:** 2026-02-24
**Authors:** Lead Dev + Architect

---

## Problem

When a user wants to practice a specific weak answer, how do we define "a segment" and what does rewinding mean in practice?

Four sub-problems:

1. **Segment boundary** — Where does one answer end and another begin?
2. **Audio vs text** — Rewind = audio replay? Or re-ask the question?
3. **Scoring consistency** — Same rubric, or a different "rewind rubric"?
4. **Delta computation** — What does "improvement" mean numerically?

---

## Options Considered

### Option A: Audio timestamp rollback

- Store audio buffer at each segment boundary.
- Rewind = replay audio from that point.
- User re-records their answer over the original.
- **Rejected**: Audio NEVER stored (spec constraint, privacy requirement).
  Also breaks if user reconnects on a new device.

### Option B: Re-ask same question, re-score answer text

- Segment = one (question, answer) pair from transcript.
- Rewind = AI re-asks the same question.
- User types or speaks their improved answer.
- Re-score with SAME Scorer class, SAME rubric.
- Delta = new_score - original_score.
- **Selected** ✅

### Option C: Holistic session rewind

- Re-run the entire session from a specific segment forward.
- Preserves conversation context.
- Complexity: requires session state management, voice pipeline restart.
- **Rejected for MVP**: Simpler segment-level rewind is sufficient.

### Option D: Guided improvement (fill in the blanks)

- Instead of re-answering, user fills in specific missing elements.
- E.g., "Add a metric to this sentence: [original sentence]".
- More guided but less authentic to real interview practice.
- **Rejected**: Real rewind from scratch is more valuable for deliberate practice.

---

## Decision

**Segment = one question-answer pair. Rewind = re-ask + re-score + delta.**

### Segment definition

```
Transcript turn sequence:
  [assistant] "Tell me about a challenge." ← question boundary
  [user]      "I fixed a slow query."      ← answer start
  [user]      "It improved performance."   ← answer continues
  [assistant] "Can you quantify that?"     ← next question boundary
```

`_extract_qa_segments()` in `app/api/v1/scoring.py` implements this split.

### Rewind flow

```
POST /sessions/{id}/rewind
  body: {segment_id}
  → returns: question + hint (what to fix) + original_score

POST /sessions/{id}/rewind/{segment_id}/score
  body: {answer_text}
  → re-scores with Scorer class
  → computes delta
  → updates segment.rewind_count + best_rewind_score
  → updates skill graph
  → returns: {original_score, new_score, delta, rules_fixed, rules_new, reason}
```

### Hint generation

The hint is built from the top 2 `fix` strings in `rules_triggered` from the original scoring.
This gives the user a concrete objective for their re-answer without being prescriptive.

### Delta computation

```
delta = new_score - original_score

Category delta (per dimension):
  structure_delta = new.structure - original.structure
  ...etc

Rules fixed = original_rules - new_rules (no longer triggered)
Rules new   = new_rules - original_rules (newly triggered)

Reason = human-readable summary combining delta, rules_fixed, biggest category change.
```

### Scoring consistency

Same `Scorer` class, same rubric, same model routing (based on session quality_profile).
No special "rewind rubric." Consistent evidence-based scoring ensures delta is meaningful.

---

## Tradeoffs Accepted

| Tradeoff | Rationale |
|---|---|
| Text-only rewind in MVP (not voice) | Voice rewind requires spawning a new voice session. Complexity deferred. Text answer still exercises the same skills. |
| Re-scoring costs API call | Same cost as original scoring. Tracked in usage_logs. User gets real signal. |
| No undo on rewind | rewind_count only goes up. best_rewind_score tracks high water mark. |
| Hint based on top 2 rules only | 2 focused objectives > overwhelming list of 8 fixes. Deliberate practice principle. |

---

## Measured Results

*To be filled after first rewind usage:*

- avg_delta_per_rewind: TBD (target > +10 points)
- rewind_usage_rate: TBD (target > 60% of scored sessions)
- rules_fixed_per_rewind: TBD
- time_to_pass_threshold: TBD
