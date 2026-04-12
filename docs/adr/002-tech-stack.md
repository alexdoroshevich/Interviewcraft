# ADR-002: Technology Stack

**Date:** 2026-02-24
**Status:** Accepted
**Deciders:** Project owner + Claude Opus + ChatGPT + Gemini (consensus)

---

## Problem

Selecting the full technology stack for InterviewCraft's backend, frontend, database, voice pipeline, and AI providers. Decisions need to support real-time voice (<800ms E2E), JSONB-flexible skill graph, streaming LLM output, and cost-efficient operation.

---

## Options Considered and Decisions

### Backend Framework

| Option | Decision | Reason |
|--------|----------|--------|
| **FastAPI (Python 3.13)** | ✅ Selected | Async-native, WebSocket support, Pydantic validation, Python AI ecosystem |
| Express/Node.js | ❌ | Less mature AI/ML ecosystem; type safety weaker |
| Go Fiber | ❌ | No AI library ecosystem; more boilerplate for ML tasks |
| Django | ❌ | Sync-by-default; WebSocket support is bolted on |

### Database

| Option | Decision | Reason |
|--------|----------|--------|
| **PostgreSQL 16 + JSONB** | ✅ Selected | JSONB for skill graph (no migrations per new skill), vector extension, battle-tested |
| MySQL | ❌ | Weaker JSONB support |
| MongoDB | ❌ | No ACID transactions; joins painful |
| Supabase | ❌ | Vendor lock-in; PostgreSQL underneath anyway |

**Critical decisions:**
- `transcript_words` in a **separate table** (TTL 14 days), NOT in session JSONB
- JSONB columns: `transcript`, `lint_results`, `skills`, `evidence_links`, `diff_versions`
- `pgcrypto` extension for `gen_random_uuid()`

### Auth

| Option | Decision | Reason |
|--------|----------|--------|
| **JWT (python-jose) + bcrypt(12)** | ✅ Selected | Stateless, easy horizontal scaling, industry standard |
| Session cookies (server-side) | ❌ | Requires sticky sessions or Redis session store |
| Passkeys / WebAuthn | ❌ | Phase 2 — reduces friction at MVP for a developer audience |

**JWT design:**
- Access token: 15 min, returned in response body (Bearer)
- Refresh token: 7 days, httpOnly SameSite=Lax cookie
- Account lockout: 5 failures → 15-min cooldown (tracked in `users.locked_until`)
- Rate limiting: 5 req/60s per IP via Redis on auth endpoints

### Voice Pipeline

| Option | Decision | Reason |
|--------|----------|--------|
| **Pipecat** | ✅ Selected | Open-source, built for AI voice, VAD/STT/LLM/TTS orchestration |
| LiveKit | ❌ | WebRTC-focused, more complex setup, requires STUN/TURN |
| Custom pipeline | ❌ | Reinventing Pipecat; high maintenance |

**Transport:** WebSocket (not WebRTC) — full server-side control, session recovery, simpler.

### STT

| Option | Decision | Reason |
|--------|----------|--------|
| **Deepgram Nova-2** | ✅ Selected | Lowest latency streaming WebSocket, word-level timestamps, $0.0058/min |
| Whisper API | ❌ | No real-time streaming; batch only |
| Google STT | ❌ | Higher latency, more complex auth |
| AssemblyAI | ❌ | Higher cost; no streaming word timestamps |

### LLM

| Option | Decision | Reason |
|--------|----------|--------|
| **Claude Sonnet (voice/scoring) + Haiku (diff/memory)** | ✅ Selected | Best instruction following for rubric; streaming JSON; prompt caching |
| GPT-4o | ❌ | Scoring calibrated to Claude Sonnet; switching = re-calibrate golden set |
| Gemini | ❌ | Same calibration concern |

**ProviderSet per-task routing (not a single LLM):**
- `voice_llm`: Sonnet (all profiles)
- `scoring_llm`: Sonnet (Quality), Haiku (Balanced/Budget)
- `diff_llm`: Haiku (ideal version uses Sonnet)
- `memory_llm`: Haiku + Anthropic Batch API (50% cheaper, async OK)

### TTS

| Option | Decision | Reason |
|--------|----------|--------|
| **ElevenLabs Turbo v2.5** (Quality) | ✅ Selected | Most natural, lowest streaming latency, $0.06/1K chars |
| **Deepgram Aura-1** (Budget) | ✅ Selected | 4× cheaper ($0.015/1K chars), same Deepgram ecosystem |
| Google Cloud TTS | ❌ | Less natural voice |
| PlayHT | ❌ | Higher latency |

### Frontend

| Option | Decision | Reason |
|--------|----------|--------|
| **Next.js 15 (App Router)** | ✅ Selected | SSR for landing page SEO, App Router for streaming, TypeScript, Vercel deploy |
| Remix | ❌ | Smaller ecosystem; less mature App Router equivalent |
| Vite + React SPA | ❌ | No SSR; SEO penalty on landing page |

**State:** Zustand — minimal boilerplate, no provider hell.
**Charts:** Recharts — for metrics dashboard.

### Cache

**Redis 7** — session state, WebSocket pub/sub, rate limiting (TTL-based). Standard.

### Vector DB

**ChromaDB** — embedded, no separate service in dev, sufficient for 50K questions. Added **Weeks 5-6**, not needed until question bank.

### Logging

**structlog** — JSON structured logs, `scrub_secrets` processor redacts `sk-ant-*`, `dg_*`, `el_*` patterns from all log output. NEVER log PII, transcripts, or user answers.

### CI/Deploy

- **CI:** GitHub Actions (free for public repos)
- **Deploy:** Fly.io (backend — Docker, stateful WebSocket) + Vercel (frontend — CDN, SSR)
- **License:** MIT

---

## Tradeoffs Accepted

1. **Python over Go/Node** — slightly lower raw throughput, but AI ecosystem + async FastAPI is sufficient for <100 concurrent users at MVP
2. **PostgreSQL JSONB over dedicated graph DB** — skill graph is 20-30 nodes; a graph DB adds complexity without benefit at this scale
3. **JWT over sessions** — no server-side session storage needed; refresh token rotation is secure enough for MVP
4. **No BYOK at MVP** — provider abstractions are in place; BYOK shipped in Phase 2 (Fernet encryption, per-session key decryption, `DELETE /api/v1/settings/byok`)

---

## Measured Result

_(From benchmarks/ suite — see benchmarks/README.md for methodology)_

- Voice pipeline E2E latency: p95 = 940ms (STT→LLM→TTS, mock providers)
- Scoring Pearson r vs. human judgement: 0.91 (MAE = 6.2 pts)
- Scoring variance on golden set: avg 4.1 pts, max 7 pts (target: < 8)
- Memory recall accuracy: 95%, hallucination rate: 0%
