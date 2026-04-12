# ADR-006: Privacy and Data Retention

**Status:** Accepted
**Date:** 2026-02-24

---

## Problem

InterviewCraft handles sensitive personal data: voice recordings, interview answers, salary figures, career stories, and performance scores. What do we store, how long, and how do we protect it?

---

## Decision

### What we store (and why)

| Data | Storage | Duration | Justification |
|---|---|---|---|
| Session transcript (text) | PostgreSQL JSONB (AES-256) | User lifetime | Needed for scoring, rewind, story detection |
| Word-level timestamps | `transcript_words` table | 14 days TTL | Evidence spans; old sessions lose exact quotes but retain `{start_ms, end_ms}` |
| Audio recordings | **Never stored** | 0 | Lives only in WebSocket buffer during active session |
| Skill graph | PostgreSQL JSONB | User lifetime | Core feature — persistent memory |
| Stories | PostgreSQL | User lifetime | User's personal career narratives |
| Negotiation context | PostgreSQL (session JSONB) | User lifetime | Track patterns across rounds |
| Usage logs (cost/latency) | PostgreSQL | 90 days | Operational metrics; no PII |
| API keys | **Never stored** | 0 | Provider keys in env only; user keys not accepted in MVP |

### Encryption

- Transcripts and session data: PostgreSQL AES-256 via pgcrypto extension.
- Keys managed via environment variables, not stored in DB.
- Auth tokens: HS256 JWT with short TTL (15 min access, 7 day refresh).
- Passwords: bcrypt with cost factor 12.

### Logging rules (enforced in CLAUDE.md)

- NEVER log: transcripts, answers, names, emails, negotiation amounts.
- ALWAYS log: session_id, latency_ms, cost_usd, error type (not message content).
- Structlog key-scrubbing processor: redacts `sk-ant-*`, `dg_*`, `el_*` patterns.

### Right to deletion

- `DELETE /api/v1/auth/me/delete` (Phase 2) cascades: sessions, scores, skill_graph, stories.
- Until then: database CASCADE on `users.id` deletion handles cleanup.

### Data minimization

- No email collection beyond authentication.
- No IP logging beyond rate limiting (Redis TTL 1 minute).
- No analytics or third-party tracking in MVP.

---

## Tradeoffs

| Tradeoff | Rationale |
|---|---|
| Transcripts stored long-term | Required for rewind, scoring, story detection. User can delete account. |
| 14-day word timestamp TTL | Enough for active sessions; reduces storage. Old rewinds fall back to utterance-level. |
| No audio storage | Simplifies privacy. Rewind = re-ask (not replay). Spec constraint. |
| pgcrypto vs application-level encryption | Application-level Fernet encryption shipped in Phase 2 for BYOK keys. `users.byok_keys` JSONB uses Fernet; all other user data uses PostgreSQL-level security. |
