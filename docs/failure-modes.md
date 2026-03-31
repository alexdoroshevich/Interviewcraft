# InterviewCraft — Failure Modes & Degradation Strategies

> How the system degrades gracefully when components fail.

---

## Design Principle

InterviewCraft is built on the assumption that external AI APIs will occasionally fail.
The degradation hierarchy:
1. **Use cached/stored result** (no external call needed)
2. **Defer to async retry** (scoring can wait, voice cannot)
3. **Surface actionable error** to user (not a spinner forever)
4. **Fall back to cheaper provider** (Budget profile)
5. **Degrade feature, not session** (session continues, scoring skipped)

---

## Failure Mode Matrix

| Component | Failure | Impact | Degradation |
|---|---|---|---|
| Anthropic (voice LLM) | 5xx / timeout | Voice response missing | Show "I need a moment, please repeat" after 8s. Retry once. |
| Anthropic (scoring) | Parse failure | Score not shown | JSON retry (up to 2x). Track `json_parse_fail_rate`. Show "Scoring pending" in UI. |
| Anthropic (cache miss) | Cache evicted | Higher cost | Transparent — cache re-warms on next call. Log `cached=false`. |
| Deepgram STT | Connection drop | Voice input lost | WebSocket auto-reconnect (3 attempts, exponential backoff: 1s, 2s, 4s). |
| Deepgram STT | Low confidence (<60%) | Mishear | `"I didn't catch that — could you repeat?"` injected as LLM message. |
| ElevenLabs TTS | Synthesis failure | No audio output | Fall back to Deepgram Aura-1 TTS. If both fail: return transcript text only. |
| PostgreSQL | Connection timeout | DB unavailable | FastAPI returns 503. WebSocket closes with code 1011. |
| Redis | Connection refused | Rate limits disabled | Rate limiter logs warning, allows request through (fail-open for UX). |
| WebSocket | Browser disconnect | Session orphaned | Session stays in `active` state. Next visit: show "Resume session?" prompt. |
| Memory extraction | Batch API timeout | Skill graph not updated | Skill update deferred — runs on next session start via lazy refresh. |

---

## Specific Scenarios

### Voice session mid-flight when Anthropic goes down

1. LLM streaming stops mid-sentence.
2. TTS sends partial buffer (whatever was generated before failure).
3. Backend logs `event=voice_llm.failed`.
4. After 8 seconds of silence, injected message: *"I'm having trouble connecting — let's take a short break."*
5. Session remains `active`. User can re-enter the voice session.
6. On re-entry, the last question is re-asked (from segment state in DB).

### Scoring fails (JSON parse error)

1. First attempt returns malformed JSON.
2. Repair prompt sent: `"Fix this JSON: <truncated_response>"` (up to 200 tokens).
3. If repair succeeds: score saved with `confidence=low`, `repair_attempted=true`.
4. If repair fails after 2 attempts: segment saved with `overall_score=null`, `confidence=null`.
5. UI shows `SegmentScore` card with `"Scoring pending — check back later"`.
6. `json_parse_fail_rate` tracked in `usage_logs.operation="scoring_repair"`.

### Database write fails mid-session

1. Transcript buffered in WebSocket memory throughout session.
2. On `PATCH /sessions/{id}` (end session): if DB write fails, return 503.
3. Frontend retries end-session call up to 3 times (5s intervals).
4. If all fail: transcript shown in browser console (escape hatch), user can copy.

### All providers down simultaneously

1. `/health` endpoint still returns `{"status":"ok"}` (process alive).
2. Admin metrics `/api/v1/admin/metrics` shows `sample_count=0` (no new data).
3. All existing data (dashboard, skills, stories, history) still loads from DB.
4. New voice sessions: error page `"Voice sessions temporarily unavailable. Your practice data is safe."`.

---

## Error Messages (User-Facing)

| Code | User sees | Meaning |
|---|---|---|
| 401 | "Session expired — please log in again" | JWT expired |
| 403 | "Admin access required" | Not admin role |
| 429 | "Too many requests — please wait 1 minute" | Rate limit hit |
| 503 | "Service temporarily unavailable" | DB/provider down |
| WebSocket 1011 | "Connection error — session saved, please reconnect" | Server error |
| WebSocket 1008 | "Session ended by server — please log in" | Auth failure |

---

## What Never Fails (by design)

- **Past sessions are always readable** — stored in PostgreSQL, no external dependency.
- **Skill graph is always readable** — same.
- **Story bank always works** — pure DB CRUD.
- **Offline demo** (`scripts/run_demo.sh`) works without any API keys.
