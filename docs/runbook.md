# InterviewCraft — Operations Runbook

> For on-call and production debugging. Last updated: 2026-02-25

---

## Health Checks

| Endpoint | Expected | Meaning |
|---|---|---|
| `GET /health` | `{"status":"ok"}` | Process alive |
| `GET /api/v1/admin/metrics` | 200 + latency data | DB + services up |
| Redis: `docker compose exec redis redis-cli ping` | `PONG` | Redis live |
| Postgres: `docker compose exec postgres pg_isready` | `accepting connections` | DB live |

---

## High Latency (E2E p95 > 1000ms)

**Symptom:** Admin metrics shows e2e_p95 > 1000ms. Users report slow voice responses.

**Triage steps:**

1. **Isolate the component:**
   - Check `session_metrics` breakdown: which sub-latency is high?
   - `stt_latency_ms` high → Deepgram issue (check [status.deepgram.com](https://status.deepgram.com))
   - `llm_ttft_ms` high → Anthropic overloaded or prompt too long
   - `tts_latency_ms` high → ElevenLabs issue or TTS buffer too large

2. **Anthropic TTFT > 800ms:**
   ```sql
   SELECT AVG(llm_ttft_ms), MAX(llm_ttft_ms), COUNT(*)
   FROM session_metrics
   WHERE created_at > NOW() - INTERVAL '1 hour';
   ```
   - If consistently high: check if rubric prompt caching is working
   - `SELECT cached, COUNT(*) FROM usage_logs WHERE provider='anthropic' AND created_at > NOW() - INTERVAL '1 hour' GROUP BY cached;`
   - If `cached=false` dominates: cache evicted — restart backend to re-warm

3. **Deepgram STT slow:**
   - Check Deepgram dashboard for regional latency spikes
   - Fallback: edit `PROVIDER_PROFILE=budget` in env → switches to Deepgram Aura-1 TTS, same STT

4. **Connection issues:**
   - Check WebSocket keep-alive: default timeout 60s
   - Browser console: look for `1006 Abnormal Closure` → network interruption

---

## Provider Failures

### Anthropic down
- Error pattern: `anthropic.APIStatusError` or `APIConnectionError`
- Impact: scoring, diff, memory extraction fail; voice LLM fails
- **Mitigation:** Sessions stay in `active` state. Scoring is async — retry on next request.
- Check: `https://status.anthropic.com`

### Deepgram down
- Error pattern: WebSocket to `wss://api.deepgram.com` closes immediately
- Impact: STT fails, voice session can't start
- **Mitigation:** Display error to user: "Speech-to-text temporarily unavailable"
- Log: `event=stt.connection_failed` in structlog output

### ElevenLabs down
- Error pattern: `elevenlabs.APIError` on TTS synthesis
- Impact: AI voice response silenced
- **Mitigation:** Fall back to Deepgram Aura-1 TTS (Budget profile) by setting `TTS_PROVIDER=deepgram_aura`

---

## Low Cache Hit Rate (< 70%)

**Symptom:** Admin metrics `cache_hit_rate_pct < 70`. Cost per session increases.

**Root cause:** Anthropic's ephemeral prompt cache has a 5-min TTL. If sessions are sparse,
cache expires between calls.

**Fix:** Ensure the scoring rubric (cached prefix) is identical across calls:
- Check `app/services/scoring/rubric.py` — the rules list must not change at runtime
- Restart backend if cache seems stale (re-warms on first request per process)

---

## Database Issues

### Migration failed
```bash
# Check current head
docker compose exec backend alembic current

# Show migration history
docker compose exec backend alembic history --verbose

# Rollback one step
docker compose exec backend alembic downgrade -1
```

### Disk full (transcripts growing)
```sql
-- Check table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Purge old word timestamps (TTL 14 days enforced manually)
DELETE FROM transcript_words WHERE created_at < NOW() - INTERVAL '14 days';
```

---

## Redis Issues

### Rate limit keys stuck
```bash
# List all rate limit keys
docker compose exec redis redis-cli KEYS "ratelimit:*"

# Clear a specific IP
docker compose exec redis redis-cli DEL "ratelimit:192.168.1.1"
```

### Session state lost after Redis restart
- Sessions in `active` state with no Redis entry are safe — they'll timeout naturally
- WebSocket clients will reconnect and create a new session state

---

## Log Filtering

All logs are structlog JSON. Key fields:

```bash
# Filter by session
docker compose logs backend | grep '"session_id":"<UUID>"'

# All errors in last hour
docker compose logs --since 1h backend | grep '"level":"error"'

# Scoring failures
docker compose logs backend | grep '"event":"scorer.'

# Cost spikes
docker compose logs backend | grep '"event":"usage.logged"' | jq '.cost_usd' | sort -n | tail -20
```

---

## Restart Procedures

```bash
# Restart backend only (zero-downtime with multiple replicas)
docker compose restart backend

# Full restart
docker compose down && docker compose up -d

# Database only
docker compose restart postgres
```
