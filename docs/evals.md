# Interviewcraft evaluation: what is tested and what is not established

Reviewed 6 November 2026. This is methodology and implementation status, not a claim of calibrated hiring/readiness accuracy.

## Offline component checks

From `backend` with dev dependencies installed:

```sh
python -m pytest -m "not integration and not nightly" -q
python -m pytest tests/test_portfolio_regressions.py -q
```

Existing sources: `tests/scoring/test_golden_answers.py`, `tests/test_scorer_utils.py`, `tests/services/memory/test_memory_loader.py`, `test_memory_builder.py`, `tests/test_voice_providers.py`, `tests/services/voice/test_interfaces.py`. There is no `tests/scoring/test_evidence.py` or `scripts/variance_report.py` in this checkout; do not use their former documentation links as executable checks.

Golden-answer data is `tests/scoring/golden_answers.json`. Offline rubric/segmentation/scorer tests use mocks; deterministic fake responses do not establish deterministic model behavior. The earlier400-test/40-deselected report was historical. The current review records separate baseline and final test outputs for the actual source revision; it makes no inference about real providers from those tests.

## Paid, explicit real-model checks

The existing markers are `integration` and `nightly`; there is no registered `lite` marker. From backend, only after an owner-approved budget and credentials:

```sh
python -m pytest tests/scoring/test_golden_answers.py -m "integration and not nightly" -v
python -m pytest tests/scoring/test_golden_answers.py -m nightly -v
```

Inspect current parametrization/run counts before starting; these commands can make repeated paid requests and repairs. The CI definitions are source configuration, not evidence an account supplies keys or hosted checks passed. The frontend CI E2E job exercises the landing page, not microphone→score→memory. Do not run live tests automatically to make a review look complete.

## Interpretation

- The rubric and JSON schema constrain requested structure. `_call_anthropic()` currently does not set temperature. Caching and even a hypothetical temperature 0 do not guarantee identical answers.
- The model chooses timestamp spans; the server extracts matching stored transcript words using offset/tolerance. This tests quote provenance separately from STT correctness, span relevance, rule applicability and scoring correctness. A quote can be null or misinterpreted.
- Hand-authored/synthetic expected scores are test references, not independently validated human labels. Correlation with them is not objective interview quality or hiring prediction.
- Synthetic `benchmarks/*/results/example.json` values are format examples, not measured results. The offline latency simulator is not STT/LLM/TTS performance evidence. Historical saved outputs require provenance/conditions before being promoted as current measurements.
- Record source commit or source hashes, model/provider versions, prompt/rubric/schema hashes, input cases, run count, retries, token usage, timing definition, raw responses, failed cases and manual criteria. Retain failures; do not report only successful runs. Do not assert an achieved KPI without this evidence.

## Full application protocol (not implied by unit tests)

Begin a local session → exchange voice audio → interrupt generation/playback → controlled primary-TTS failure → end session → trigger scoring and inspect spans → wait for PostgreSQL memory update → start another session and verify Redis/DB-loaded memory. Capture network/provider failures and spending ownership without printing keys. This requires local services, microphone and an approved provider budget. A homepage200/static demo is not this protocol. No full live protocol or new paid evaluation was run in this review.
