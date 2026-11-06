# ADR-008: Scoring variability and validation

Status: design intent retained; claims aligned to implementation 6 November 2026.

## Decision and limits

Use an explicit rubric, structured output, versioned inputs and repeated evaluations to investigate variability. The current scorer sends the rubric with an ephemeral cache breakpoint and a JSON tool schema. It **does not explicitly set temperature**. Neither prompt caching nor temperature 0 guarantees identical outputs. Reusing eligible prompt computation is not deterministic generation or proof of reduced scoring variance.

Schema structure and bounded JSON-repair attempts improve parse handling, not correctness of evidence interpretation or scores. The code can reuse the medium rewrite when an ideal rewrite is absent. Direct scoring remains Anthropic-specific; provider interfaces elsewhere do not prove model-independent calibration.

## What must be measured

Variance/range/expected-rule thresholds in the golden-answer tests are evaluation targets. Real repeated calls are marked `integration` and/or `nightly`; ordinary offline tests use mocks. No achieved variance bound, cache-hit percentage, latency or per-session saving is asserted here without the corresponding raw run, source/model/configuration and conditions. Current runnable commands and existing references: [evals](../evals.md).

Extracted transcript quotes and semantic assessment are separate: inspect both the selected time span and the model's reasoning/rule application. A correct quote does not validate its interpretation, prove improvement or establish an objective hiring/readiness score.
