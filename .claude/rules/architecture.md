---
paths:
  - "backend/app/**"
  - "docs/adr/**"
---

# Architecture Rules

These rules are non-negotiable. Violating them breaks the core product invariants.

## Evidence System
- Evidence is always `{start_ms, end_ms}` timestamp spans
- The **server** extracts quotes from transcripts using these spans
- The LLM **never** generates or fabricates quotes
- Word-level timestamps go in `transcript_words` table (TTL 14 days), NOT in session JSONB

## Audio Handling
- Audio is **never** stored to disk — it lives only in WebSocket memory
- No temporary files, no S3, no local storage for audio data
- Audio flows: microphone → WebSocket → STT provider → discard

## Provider Architecture
- STTProvider, LLMProvider, TTSProvider are abstract base classes (ABCs)
- All voice providers must implement the appropriate ABC
- Never call a provider API directly — always go through the interface
- ProviderSet has per-task LLMs: `voice_llm`, `scoring_llm`, `diff_llm`, `memory_llm`
- Never use a single LLM for all tasks — each task has its own cost/quality profile

## The Killer Loop
```
ANSWER → LINT (evidence) → DIFF (3 versions) → REWIND → DELTA → SKILL GRAPH → DRILL PLAN
```
Every feature must strengthen this loop. If a proposed change doesn't serve the loop, question whether it belongs in the product.

## Cost Awareness
- Log every API call cost to `usage_logs` table
- Use Anthropic prompt caching (rubric = cached prefix) — caching is now **automatic** server-side as of 2026; still structure prompts with stable prefix first
- Use Haiku for scoring/diff/memory in Balanced profile, Sonnet for voice
- Memory extraction uses Batch API (50% cheaper)
- Never add an LLM call without considering its cost profile
- Use `effort` parameter (replaces `budget_tokens`) for extended thinking calls
- Use `output_config.format` for structured outputs (GA as of 2026) instead of manual JSON parsing

## Anthropic Model IDs (current as of 2026-03)
- Orchestration/architecture: `claude-opus-4-6`
- Voice LLM + complex tasks: `claude-sonnet-4-6`
- Scoring/diff/memory (Balanced): `claude-haiku-4-5` (never use dated alias `claude-haiku-4-5-20251001` — kept only as legacy key in costs.py for usage_log resolution)
- **RETIRED (do not use):** `claude-3-haiku-20240307` (retires April 19 2026), `claude-3-sonnet`, `claude-3-opus`

## Database (PostgreSQL 16)
- JSONB columns >2KB that receive partial updates should use real columns — TOAST compression kills partial-update performance
- `session.profile` JSONB is acceptable (infrequent writes, small)
- Transcripts and scoring data: fine as JSONB (write-once, read-many)
- Never store word-level timestamps in JSONB — they're in `transcript_words` (TTL 14d)

## Redis (7.x)
- Set eviction policy `allkeys-lru` — prevents OOM when cache fills
- Add TTL jitter (±10%) to all cache keys to prevent thundering herd expiry
- Session state in Redis: TTL = session duration + 1 hour buffer

## Deployment (Fly.io)
- Use blue-green deployment for zero-downtime releases: deploy to `staging` machine, health-check, then swap
- Fly.io free tier removed in 2026 — all apps require paid plan
- `fly deploy --strategy bluegreen` is the correct flag
