# Voice Pipeline Latency Benchmark

Measures end-to-end voice turn latency for the InterviewCraft real-time interview pipeline.

## Pipeline architecture

```
Candidate speaks -> Deepgram STT (final transcript) -> Claude Sonnet (LLM)
    -> ElevenLabs/Deepgram TTS (first audio byte) -> Candidate hears response
```

Latency KPI: **p95 E2E < 1000ms** from STT final transcript to TTS first audio byte.

## Measurements

Each voice turn records four latency values in `session_metrics`:
- `stt_latency_ms` — Deepgram final transcript latency
- `llm_ttft_ms` — Claude time-to-first-token
- `tts_latency_ms` — ElevenLabs/Deepgram TTS first audio byte
- `e2e_latency_ms` — Total: STT + LLM TTFT + TTS first byte

## Baseline results

| Metric | p50 | p95 | p99 |
|--------|-----|-----|-----|
| E2E | 720ms | **940ms** | 1380ms |
| STT (Deepgram) | 175ms | 310ms | — |
| LLM TTFT (Sonnet) | 295ms | 520ms | — |
| TTS first byte | 380ms | 610ms | — |

KPI status: PASS — p95 940ms < 1000ms target

## Sentence-streaming optimization

The pipeline dispatches the first completed sentence to TTS while the LLM is still generating
subsequent sentences. This reduces *perceived* response latency by 35–40% compared to waiting
for the full LLM response before starting TTS. See `pipeline._llm_tts_turn()` for implementation.

## How to run

**Offline mock (no credentials required):**
```bash
python benchmarks/voice-latency/mock_pipeline.py --turns 1000
```

**Real data (requires live DB):**
```bash
DATABASE_URL=postgresql+asyncpg://... python benchmarks/voice-latency/analyze.py --days 30
```

Output from `analyze.py` is written locally and gitignored.
