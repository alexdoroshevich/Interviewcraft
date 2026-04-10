# Cost Profile Benchmark

Analyzes API cost efficiency of InterviewCraft across providers and session types.

## Architecture

Every API call (LLM, STT, TTS) is logged to the `usage_logs` table with:
- `provider` (anthropic / deepgram / elevenlabs)
- `operation` (voice_llm / scoring_llm / memory_build / stt / tts)
- `cost_usd` (exact amount for that call)
- `latency_ms`
- `cached` (Anthropic prompt cache hit)

## Baseline Results

### Cost per session (by quality profile)

| Profile | Avg cost/session | Notes |
|---------|-----------------|-------|
| Balanced | $0.031 | Haiku for scoring/memory, Sonnet for voice |
| Quality | $0.078 | Sonnet for all operations |

### Per-provider breakdown

| Provider | Operation | Avg cost/call | Avg latency |
|----------|-----------|--------------|-------------|
| Anthropic | voice_llm (Sonnet) | $0.0041 | 312ms |
| Anthropic | scoring_llm (Haiku) | $0.0018 | 1850ms |
| Anthropic | memory_build (Haiku) | $0.0004 | 420ms |
| Deepgram | stt | $0.0012 | 178ms |
| ElevenLabs | tts | $0.0019 | 390ms |

### Anthropic prompt cache performance

| Metric | Value |
|--------|-------|
| Cache hit rate | 71.2% |
| Note | Rubric prefix (~4K tokens) cached per session |

## How to run

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@host/db python benchmarks/cost-profile/query.py
```

Output goes to stdout only. `results/example.json` shows the output schema.

## Key insight: Prompt caching saves ~70% on scoring costs

The scoring rubric (~4,000 tokens) is a stable prefix that gets cached automatically by Anthropic's
server-side caching. Every subsequent scoring call in a session hits the cache, reducing effective
input token cost by ~70% for the rubric portion.
