# InterviewCraft — Security Model

> Threat model, data flow, and encryption details. Last updated: 2026-04-11

---

## Threat Model

InterviewCraft processes sensitive personal data: voice responses, interview answers,
salary figures, and career stories. The users are job-seekers — people in a vulnerable
position who need to trust the tool.

### Assets to protect

| Asset | Sensitivity | Protection |
|---|---|---|
| Session transcripts | High — career narratives | AES-256 at rest, TLS in transit |
| Salary / negotiation data | High — financial info | Same as transcripts |
| Stories | High — personal narratives | Same as transcripts |
| Skill scores | Medium | Stored plaintext (not PII in isolation) |
| Email | Medium | Not logged, bcrypt hashed passwords |
| API keys | Critical | Never stored, env vars only |
| Audio | Critical | **Never stored** — in-memory only |

### Threat actors

1. **External attacker** (most likely) — credential stuffing, injection, scraping
2. **Insider threat** — logging PII accidentally, misconfigured DB permissions
3. **Third-party AI providers** — sending sensitive data to Anthropic/Deepgram/ElevenLabs

### Out of scope (MVP)

- Nation-state adversaries
- Physical access to servers
- Client-side attacks (XSS mitigated by Next.js CSP defaults)

---

## Authentication

- **Passwords:** bcrypt with cost factor 12. Never stored in plaintext or logs.
- **JWT:** HS256, 15-min access token, 7-day refresh token (httpOnly cookie).
- **Account lockout:** 5 failed attempts → 15-min lockout. Prevents brute-force.
- **Rate limiting:** 5 req/min per IP on all auth endpoints (Redis TTL 60s).
- **Google OAuth:** authlib flow. Google ID stored, no password for OAuth users.

---

## Data Encryption

### At rest
- PostgreSQL transcripts and session JSONB: AES-256 via pgcrypto extension (`pgp_sym_encrypt`).
- Encryption key: `SECRET_KEY` environment variable (never in DB, never logged).
- Skill graph, usage logs: stored plaintext (not PII in isolation).

### In transit
- All HTTP over TLS (Fly.io terminates TLS at load balancer; Vercel handles frontend HTTPS).
- WebSocket: `wss://` (TLS).
- Internal service communication (backend ↔ Postgres ↔ Redis): within Docker network, plaintext acceptable for MVP; VPC isolation in prod.

### Audio (special case)
- Audio is **never stored to disk**.
- Lives only in WebSocket buffer during active session (~10 seconds sliding window for VAD).
- Forwarded directly to Deepgram API (TLS). Deepgram's privacy policy applies.

---

## Logging Rules

Enforced by `structlog` key-scrubbing processor (`app/logging.py`):

**NEVER log:**
- Transcript content or answer text
- User names, emails, or any PII identifiers
- Negotiation amounts or salary figures
- JWT tokens (full string)
- API keys

**ALWAYS log:**
- `session_id` (UUID — not PII)
- `latency_ms`, `cost_usd`
- Error type (not error message content if it might contain PII)
- `event` name (structured key)

**Automatic scrubbing patterns:**
```python
SCRUB_PATTERNS = ["sk-ant-*", "dg_*", "el_*", "Bearer "]
```

---

## API Key Management

### Platform keys (Anthropic, Deepgram, ElevenLabs)
- Stored only in `backend/.env` and Fly.io secrets.
- **Never** committed to git (`.gitignore` covers `.env`).
- **Never** stored in the database.
- Rotation: update Fly.io secret → restart backend. No DB migration needed.

### BYOK — user-supplied keys (shipped Phase 2)
- Users may provide their own provider keys via `POST /api/v1/settings/byok`.
- Keys are encrypted with symmetric encryption before writing to `users.byok_keys JSONB`.
  Implementation: `app/services/byok.py`.
- Decryption happens **in memory only** at WebSocket session start — the
  plaintext key exists for the lifetime of one pipeline object, then is discarded.
- Keys are never logged, never returned in API responses, and never visible
  to InterviewCraft staff.
- `DELETE /api/v1/settings/byok/{provider}` removes the encrypted entry.

---

## RBAC

Two roles: `user` (default) and `admin`.

- `admin` role gates: `GET /api/v1/admin/metrics` only in MVP.
- Admin accounts created manually via DB update (no self-registration to admin).
- `get_current_admin` dependency raises 403 for any non-admin request.

---

## Rate Limiting

| Endpoint group | Limit |
|---|---|
| `POST /api/v1/auth/*` | 5 req/min/IP |
| `POST /api/v1/sessions` | 10 req/min/user |
| `POST /api/v1/negotiation/start` | 5 req/min/user |
| All others | 60 req/min/user (Redis sliding window) |

Implementation: Redis `INCR` + `EXPIRE` per `(user_id|IP, endpoint_prefix)` key.

---

## Data Minimization

- No email collection beyond authentication.
- No IP logging beyond rate limiting (1-min TTL Redis keys, no DB persistence).
- No third-party analytics or tracking scripts (no GA, no Segment, no Mixpanel) in MVP.
- Word-level timestamps: 14-day TTL — old sessions lose exact quote timestamps but retain score data.

---

## Third-Party Data Sharing

| Provider | Data sent | Their policy |
|---|---|---|
| Anthropic | Transcript text, interview answers (for scoring/voice) | [anthropic.com/privacy](https://anthropic.com/privacy) |
| Deepgram | Audio stream (for STT) | [deepgram.com/privacy](https://deepgram.com/privacy) |
| ElevenLabs | LLM response text (for TTS synthesis) | [elevenlabs.io/privacy](https://elevenlabs.io/privacy) |

Users are informed of this via the sign-up screen before first session.

---

## Incident Response

1. **Suspected data breach:** Rotate `SECRET_KEY` immediately (invalidates all JWTs), rotate all provider API keys, notify affected users.
2. **Accidental PII in logs:** Purge log entries, update scrubbing patterns, redeploy.
3. **SQL injection attempt:** FastAPI + SQLAlchemy ORM parameterizes all queries. Monitor for unusual query patterns in logs.
4. **Compromised JWT secret:** Rotate `JWT_SECRET_KEY`, all tokens immediately invalid, users re-authenticate.
