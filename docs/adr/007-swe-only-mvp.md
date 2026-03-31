# ADR-007: SWE-Only MVP Scope

**Status:** Accepted
**Date:** 2026-02-24

---

## Problem

Should InterviewCraft support multiple professions at launch (SWE, PM, Design, Data Science) or focus on SWE only?

---

## Decision

**SWE-only for MVP.**

### Why SWE only

1. **Rubric calibration cost**: Each profession needs its own 15+ rules, golden answer test suite (30+ cases × 5 runs), and human calibration. That's weeks of work per profession.

2. **Author dogfoods SWE**: The best validation is using the tool yourself. Can't dogfood PM interviews.

3. **Market size is sufficient**: SWE = largest single group of tech job seekers. Not a limiting constraint.

4. **The architecture IS extensible**: Provider ABCs, question bank skills_tested[], and rubric rules are data-driven. Adding a new question type is config, not code.

5. **Negotiation crosses all roles**: Salary negotiation simulator works for any role. It's already in MVP.

### What "SWE" includes

- Behavioral (STAR format, leadership, conflict, mentoring)
- System Design (capacity estimation, component design, tradeoffs)
- Coding Discussion (complexity, testing, code review)
- Negotiation (anchoring, counter-strategy, equity negotiation)
- Diagnostic (5-min blitz for cold start)

### Deferred professions

| Profession | Why deferred |
|---|---|
| Product Manager | Different rubric (product sense, metrics, prioritization). Phase 2. |
| Data Scientist | SQL + statistics rubric. Phase 2. |
| Design | Portfolio-based, hard to voice-interview. Phase 3. |
| Other engineering (DevOps, Security) | Smaller market. Phase 2 if demand. |

### Extension path

When adding a new profession in Phase 2:
1. Define `{profession}_rules.py` (15+ rules, same `Rule` dataclass)
2. Add question bank entries with `type="{profession}"`
3. Add microskills to `SKILL_CATEGORIES`
4. Run golden answer calibration (30 cases)
5. Update rubric prompt prefix per session type

No schema migrations required (question type is a string field).
