# ADR-001: WebSocket vs WebRTC for Voice Transport

**Date:** 2026-02-24
**Status:** Accepted
**Deciders:** Project owner + Claude Opus + ChatGPT + Gemini (consensus)

---

## Problem

Choose a real-time audio transport for the voice pipeline between the browser and the server. The transport determines how audio flows from the user's microphone through STT → LLM → TTS and back.

---

## Options Considered

### Option A: WebRTC

WebRTC is the browser's native peer-to-peer audio protocol, designed for direct media streaming between peers.

**Pros:**
- Built into all modern browsers
- Low latency with UDP transport
- Built-in echo cancellation, noise suppression, AGC in browser audio stack
- Standard for audio conferencing products

**Cons:**
- Requires STUN/TURN server infrastructure for NAT traversal (~$20-50/mo)
- ICE negotiation adds 1-5s to connection setup
- Server must terminate WebRTC (media server like LiveKit/mediasoup = added complexity)
- Full server-side control over audio pipeline is awkward — WebRTC is P2P first
- Session recovery is complex (ICE renegotiation)
- Overkill for a single-user interview tool (no multi-party media needed)

### Option B: WebSocket (selected)

WebSocket provides a full-duplex TCP connection over HTTP. Audio is sent as binary frames.

**Pros:**
- Simple — every developer knows WebSocket
- Full server-side control (server decides when to start/stop TTS, etc.)
- Session recovery: reconnect and resume from last known state
- No STUN/TURN infrastructure required
- Works anywhere HTTP works (proxies, corporate firewalls)
- Easy to integrate with FastAPI (`@router.websocket`)
- Works with httpx for testing

**Cons:**
- TCP (not UDP) — head-of-line blocking if packets are dropped
- Higher latency than WebRTC in poor network conditions
- No native echo cancellation — must be handled in browser (RNNoise/WebAudio)

---

## Decision

**WebSocket** — for the MVP.

### Rationale

1. **Simplicity wins at MVP scale.** No STUN/TURN, no media server, no ICE negotiation. One fewer infrastructure component is a real advantage for a solo developer.

2. **Full server control is a feature.** The killer loop requires the server to control exactly when audio plays, when to send soft prompts, and when to transition state. WebSocket makes this trivial; WebRTC complicates it.

3. **Session recovery is easier.** The client can reconnect a WebSocket in 3 lines of code with exponential backoff. Recovering a WebRTC session requires ICE renegotiation.

4. **TCP is fine for interview latency targets.** Our target is p95 < 1000ms E2E. TCP jitter at typical latencies (50-100ms) does not meaningfully impact this. WebRTC's UDP advantage matters in video conferencing, not in a turn-based interview tool.

5. **All three AIs agreed.** Claude Opus, ChatGPT, and Gemini converged on WebSocket in the planning session.

---

## Implementation Details

### Audio format
- **Browser → Server:** `webm/opus` (MediaRecorder default, accepted by Deepgram)
- **Server → Browser:** PCM 24kHz raw bytes, base64-encoded in JSON frames

### WebSocket message protocol

**Client → Server (JSON):**
```json
{"type": "audio",     "data": "<base64 webm/opus bytes>"}
{"type": "end_audio"}
{"type": "interrupt"}
```

**Server → Client (JSON):**
```json
{"type": "transcript_partial", "text": "...", "x_latency": {"stt_partial_ms": 150}}
{"type": "transcript_final",   "text": "...", "x_latency": {"stt_ms": 210}}
{"type": "llm_chunk",           "text": "...", "is_final": false, "x_latency": {}}
{"type": "audio_chunk",         "data": "<base64 PCM>", "x_latency": {"tts_first_byte_ms": 95, "e2e_ms": 740}}
{"type": "session_state",       "state": "listening|processing|speaking"}
{"type": "soft_prompt",         "text": "Take your time, I'm listening."}
{"type": "error",               "message": "..."}
```

### Authentication
JWT access token passed as query parameter (`?token=<jwt>`).
Short-lived (15 min) access tokens make this acceptable for MVP.
Phase 2: evaluate cookie-based WS auth.

### Reconnection (client-side)
3 attempts with exponential backoff (1s, 2s, 4s).
Server maintains session state in PostgreSQL — reconnect resumes from last transcript position.

---

## Tradeoffs Accepted

| Tradeoff | Accepted | Reason |
|----------|----------|--------|
| TCP jitter vs UDP | Yes | Latency target (p95 < 1000ms) is achievable on TCP |
| Manual echo cancellation | Yes | RNNoise WASM in browser (Week 2) |
| No native AEC | Yes | Server-side VAD (Silero) handles false triggers |
| No TURN server | Yes | TCP WebSocket works through all firewalls |

---

## Custom Pipeline vs Pipecat

The spec recommends Pipecat for voice orchestration. After evaluation:

- Pipecat's API changes between minor versions (v0.0.x releases)
- Our provider ABC pattern makes the pipeline easily swappable
- Custom pipeline gives full control over latency instrumentation (required for DoD KPI)
- "Using Pipecat or custom" — the spec explicitly allows this

**Decision:** Custom `VoicePipeline` orchestrator in `services/voice/pipeline.py`.
Provider ABCs in `services/voice/interfaces.py` are identical to Pipecat's conceptual model.
Migration to Pipecat is mechanical work when the API stabilizes (Phase 2).

---

## Measured Result

_(To be filled after first real session)_

- p50 E2E latency: TBD ms
- p95 E2E latency: TBD ms
- STT latency: TBD ms
- LLM TTFT: TBD ms
- TTS first byte: TBD ms
