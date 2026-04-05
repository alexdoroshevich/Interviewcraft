# Feature Spec: Session Duration Limit + Countdown Timer

## What It Does

Every interview session has a configurable time limit. The UI shows a countdown timer that ticks down second by second (59:59 → 59:58 → ...). When time runs out, the session ends gracefully — exactly like a real interview.

The timer is profession- and type-agnostic. It doesn't change behavior based on who is being interviewed or what type of session it is. It simply counts down from whatever limit was agreed at session creation.

## Defaults (by session type)

| Session Type | Default | Min | Max |
|---|---|---|---|
| `behavioral` | 35 min | 15 | 60 |
| `system_design` | 50 min | 20 | 75 |
| `coding_discussion` | 35 min | 15 | 60 |
| `negotiation` | 20 min | 10 | 45 |
| `diagnostic` | 25 min | 10 | 40 |
| `debrief` | 25 min | 10 | 40 |

These defaults are grounded in real-world FAANG interview norms (April 2026 research). Users can adjust at creation time via slider or dropdown.

## User Experience

### Session creation page
- New "Duration" field, pre-filled with the session-type default
- Slider or dropdown: adjustable in 5-minute increments
- Label: "Interview time limit — this is how long your session will run"

### During session (header)
- **When limit is set**: show countdown — red-tinted when ≤ 5 minutes remaining: `12:34`
- **When no limit**: show elapsed time as today (no change to current behavior): `12:34 elapsed`
- Countdown ticks every second client-side (no server round-trips)

### Graceful end
1. At T−2 minutes: AI interviewer says naturally: *"We have about two minutes left — let's wrap up."*
2. At T−0: backend sends `{ "type": "session_state", "state": "time_limit_reached" }` via WebSocket
3. Frontend calls `handleEnd()` automatically — same flow as manual end
4. Session saves and redirects to results page

## Architecture

### Files to change

**New: `backend/alembic/versions/015_add_session_duration_limit.py`**
```sql
ALTER TABLE sessions ADD COLUMN duration_limit_minutes INTEGER NULL;
```
NULL = no limit (backwards-compatible).

**`backend/app/models/interview_session.py`**
```python
duration_limit_minutes: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
```

**`backend/app/schemas/session.py`**
```python
# In SessionCreate:
duration_limit_minutes: int | None = Field(default=None, ge=1, le=180)

# In SessionResponse:
duration_limit_minutes: int | None
```

**`backend/app/api/v1/sessions.py`**
- Pass `duration_limit_minutes` when constructing `InterviewSession`
- Pass `duration_limit_minutes` to `VoicePipeline` constructor via WebSocket handler

**`backend/app/services/voice/pipeline.py`**
Add a fifth asyncio task (`_duration_guard`) that:
1. Sleeps for `(duration_limit_minutes * 60) - 120` seconds
2. Sends a soft warning event to trigger the "2 minutes left" AI prompt
3. Sleeps 120 more seconds
4. Sends `{ "type": "session_state", "state": "time_limit_reached" }`
5. Closes the WebSocket gracefully (same teardown as normal end)

Using a separate task (not `asyncio.wait_for`) keeps teardown graceful and allows the 2-minute warning.

**`frontend/app/sessions/[id]/page.tsx`**
- Read `duration_limit_minutes` from session API response
- When set: compute `timeRemaining = (durationLimitSeconds - elapsed)` each tick
- Display as countdown: `Math.floor(timeRemaining / 60):String(timeRemaining % 60).padStart(2, '0')`
- Add CSS class `text-red-500` when `timeRemaining <= 300` (5 minutes)
- Call `handleEnd()` when `timeRemaining <= 0`
- When not set: keep current elapsed display unchanged

**`frontend/lib/useVoiceSession.ts`**
- Accept optional `durationLimitSeconds?: number`
- Handle `session_state: time_limit_reached` message → call `onEnd()` callback

### No change needed
- `tuning.py` — this is a per-session value, not a global knob
- Any other files — change is fully contained in the 6 above

## Edge Cases

| Case | Behavior |
|---|---|
| User manually ends before limit | Normal end — no limit-related message |
| WebSocket drops before limit | Normal disconnect handling — no change |
| Session created with no limit (null) | No countdown shown, no auto-end — backward compatible |
| User sets limit, then pauses session | Timer continues — mirrors real interview behavior |
| 2-minute warning during AI speaking | Warning fires anyway; AI finishes current sentence then weaves in the warning |

## What This Does NOT Do

- Does not change the per-turn `PIPELINE_HARD_CAP_S` (30s inactivity guard) — separate mechanism
- Does not restrict session type or profession — just a timer
- Does not retroactively apply to existing sessions

## Status

- [ ] Migration 015
- [ ] Model field
- [ ] Schema fields
- [ ] API pass-through
- [ ] Pipeline `_duration_guard` task
- [ ] Frontend countdown display
- [ ] Frontend auto-end on zero
