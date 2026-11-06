# Voice timing: simulation versus recorded observations

The application streams audio→STT→LLM text→sentence TTS. Its latency fields are implementation instrumentation, not verified performance. No current p95 target is claimed achieved, and no 35–40% improvement is asserted without a saved comparative run.

```sh
# Offline synthetic timing model, no API calls:
python benchmarks/voice-latency/mock_pipeline.py --turns 1000
# Existing session_metrics DB, configured DATABASE_URL; not a live voice run:
python benchmarks/voice-latency/analyze.py --days 30
```

The simulator generates assumed timings. Its percentiles must not be labelled Deepgram/Claude/ElevenLabs latency measurements or a passed production KPI. `results/example.json` is a synthetic output example. Recorded metrics also need source/model/device/network details, sample size, failures and an exact timing boundary; summing component timings is not automatically the wall-clock experience with overlapped sentence synthesis or interruptions. [Evaluation conditions](../../docs/evals.md).
