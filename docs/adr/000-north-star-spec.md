# ADR-000: North Star Specification

**Date:** 2026-02-24
**Status:** Accepted
**Deciders:** Project owner + Claude Opus + ChatGPT + Gemini (6-hour planning session)

---

## Context

InterviewCraft is a **Deliberate Practice Engine for tech interviews** — not "another AI mock interview tool." This ADR captures the north star specification so all future implementation decisions can be evaluated against it.

---

## The Killer Loop

```
ANSWER → LINT (evidence-based) → DIFF (3 versions) → REWIND (re-answer segment)
    ↑    → DELTA SCORE → SKILL GRAPH UPDATE → ADAPTIVE DRILL PLAN ──────────────┘
```

**The moat is the integration of the closed loop, not any single feature.**

---

## 9 Components (MVP)

| # | Component | Core Value |
|---|-----------|------------|
| 1 | Voice Pipeline | Real-time conversation <800ms E2E; Pipecat + Deepgram Nova-2 + Claude Sonnet + ElevenLabs |
| 2 | Evidence-Based Rubric Scoring | 15 iron rules; evidence as `{start_ms, end_ms}` spans; server extracts quotes |
| 3 | Answer Diff View | 3 versions (minimal / medium / ideal), each annotated with rule + score impact |
| 4 | Rewind & Re-Answer | Re-ask specific question that exposed weakness; instant delta score |
| 5 | Skill Graph + Adaptive Drill Plan | 20-30 microskills; spaced repetition; persistent across sessions |
| 6 | Story Bank + Coverage Map | Semi-auto extraction; gap detection; overuse warnings |
| 7 | Salary Negotiation Simulator | Multi-round; hidden budget; pattern memory across rounds |
| 8 | Level Calibration | L4/L5/L6 bar shown after every answer with specific gaps to bridge |
| 9 | Beat Your Best | Personal-best gamification per skill |

---

## Architecture Decisions

| Concern | Decision | Reason |
|---------|----------|--------|
| Real-time voice | WebSocket (not WebRTC) | Simpler, full server-side control, session recovery |
| Voice orchestration | Pipecat | Open-source, handles VAD/STT/LLM/TTS, active community |
| STT | Deepgram Nova-2 | Lowest latency streaming, word-level timestamps, $0.0058/min |
| LLM | Claude Sonnet (Anthropic) | Best rubric scoring, streaming JSON, prompt caching |
| TTS (quality) | ElevenLabs Turbo v2.5 | Most natural voice, lowest streaming latency |
| TTS (budget) | Deepgram Aura-1 | Same ecosystem, $0.015/1K chars (4× cheaper than ElevenLabs) |
| Database | PostgreSQL + JSONB | Skill graph flexibility; no schema migrations for new skills |
| Vector DB | ChromaDB | Embedded; no separate service; sufficient for 50K questions |
| Backend | FastAPI (Python 3.11) | Async WebSocket native; AI ecosystem |
| Frontend | Next.js 14 + App Router | SSR, streaming, TypeScript, Tailwind |
| State | Zustand | Minimal boilerplate; no provider hell |
| Logging | structlog | JSON structured logs; key-scrubbing processor |

---

## Critical Technical Rules

1. **Audio is NEVER stored** — lives only in WebSocket memory. Rewind = re-ask question, not audio replay.
2. **Word-level timestamps** → separate `transcript_words` table (TTL 14 days), not session JSONB.
3. **Single batched LLM call** for score + diff + memory (not three separate calls).
4. **Evidence spans** are `{start_ms, end_ms}` from LLM; server extracts actual quote from transcript.
5. **ProviderSet with per-task LLMs**: `voice_llm` (Sonnet), `scoring_llm`, `diff_llm`, `memory_llm` (Haiku).
6. **Anthropic prompt caching**: rubric + format = cached prefix (target cache hit rate > 70%).
7. **Anthropic Batch API** for memory extraction (async OK, 50% cheaper).
8. **RBAC** (user/admin roles) not IP whitelist for admin endpoints.
9. **Scoring calibrated to Claude Sonnet** — warn if swapping models.
10. **structlog** with key-scrubbing processor (redacts `sk-ant-*`, `dg_*`, `el_*` patterns).

---

## Quality Profiles

| Profile | Models |
|---------|--------|
| Quality | Sonnet (all tasks) + ElevenLabs |
| Balanced | Sonnet (voice), Haiku (scoring/diff/memory) + ElevenLabs |
| Budget | Haiku (all) + Deepgram Aura-1 TTS |

---

## Definition of Done (all 8 green = launch)

1. Voice latency p95 < 2000ms
2. Scoring variance < 8 points on golden answer set
3. JSON parse fail rate < 5%; repair success > 80%
4. Rewind delta avg > +10 points
5. Cost displayed in UI, matches selected profile
6. Cache hit rate > 70%
7. Offline demo works without any API keys
8. Dogfooding: project owner's skill graph has 10+ sessions

---

## What is Explicitly OUT of MVP

- BYOK (Bring Your Own Key) — provider abstractions ready; implementation Phase 2
- Local/offline mode — Phase 2
- Multiple professions (SWE only) — others Phase 2
- Interviewer personas (tough/friendly) — Phase 2
- Body language / video — Phase 3
- Billing/Stripe — free until 100+ users
- Company playbooks marketplace — Phase 2

---

## Consensus Points (3 AIs agreed)

1. The moat is the LOOP, not individual features
2. "Pet project → prod" = ADRs + metrics + golden tests + runbook
3. Voice pipeline + scoring stability = the two make-or-break components
4. Dogfooding is the ultimate proof
5. Build in public creates network before launch
6. Offline demo is insurance for interview day
7. BYOK adds complexity without enough MVP value — defer
8. Quality Profiles > raw model picker for UX
9. Evidence spans (server-extracted) > LLM-generated quotes
