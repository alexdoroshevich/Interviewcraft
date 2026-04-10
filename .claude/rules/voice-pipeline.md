---
paths:
  - "backend/app/services/voice/**"
  - "frontend/lib/useVoiceSession.ts"
---

# Voice Pipeline Rules

## Turn Detection
- Adaptive debounce: ~1s for short answers (<10 words), ~2.5s for long answers (≥10 words)
- Debounce measured from **last sound activity**, not last Deepgram final
- Minimum 2 words required before triggering LLM response
- `[WAIT]` escape hatch: LLM outputs `[WAIT]` if answer seems incomplete → skip TTS

## Audio Flow
- Deepgram STT → Claude LLM → ElevenLabs TTS (all streaming, concurrent)
- Deepgram: `endpointing=450ms`, keepalive pings every 5s
- ElevenLabs: `mp3_44100_128`, `optimize_streaming_latency=4`, `chunk_size=16384`
- Frontend: gapless audio via pre-scheduled Web Audio API nodes

## Barge-in
- Threshold: 80 amplitude, 10 consecutive frames (~1 second)
- Prevents headset speaker bleed from triggering false barge-in
- On barge-in: cancel current TTS, flush audio queue, resume STT

## Smart Pause
- 8-second soft prompt ("Take your time...")
- 15-second re-engage prompt
- `SmartPause.activate()/deactivate()` prevents firing during bot speech
- Deepgram keepalive pings every 5s prevent timeout during bot speaking

## Error Recovery
- TTS fallback: ElevenLabs 401 → auto-fallback to DeepgramTTSProvider
- SQLAlchemy: always `await db.rollback()` on errors in WebSocket handlers
- `transcript_rollback` message: removes premature user bubble when `[WAIT]` fires

## Never Do
- Never store audio to disk for any reason
- Never pause/resume MediaRecorder (starves Deepgram of audio data)
- Never set `sampleRate=16000` in audio constraints (let browser negotiate)
- Never log transcript content — only session_id and latency metrics
