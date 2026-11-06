# ADR-003: Timestamp-linked batched scoring

Status: accepted design, implementation notes reviewed 6 November 2026.

## Implemented path

`backend/app/services/scoring/scorer.py` sends one structured tool request per segment for score, rewritten answers and memory hints. A parse/missing-required-output failure can cause up to two repair attempts; this is not a guaranteed single billed request. The Anthropic SDK may have its own transient-error retry behavior. Quality routes scoring to Sonnet; balanced/budget use Haiku. `_ideal_model` exists but does not establish a separate ideal-model invocation on the current path.

`_SCORING_SCHEMA` defines reusable `diff_version` at the schema root so the three `#/$defs/diff_version` references resolve. Regression tests walk every local reference; local schema checks are not a live provider acceptance test. Missing ideal output can be copied from the medium output by the existing repair handling; do not present that as three independently validated rewrites.

## Evidence semantics

The model selects `{start_ms,end_ms}`. `_fill_evidence_quotes()` applies segment offset and a 200ms tolerance to stored transcript-word start times and joins matching words. No matches can produce a null quote. Transcript-grounded quote extraction prevents a free-form model quote from being treated as extracted text; it does **not** prove correct STT, correct span choice, complete evidence or a correct rule interpretation/score. A timestamp link is an inspectable reference, not objective assessment accuracy.

## Caching and costs

The rubric is sent with `cache_control: ephemeral` (default 5-minute TTL). Eligibility, token thresholds and actual usage determine whether a cache is used. Caching does not remove generation variability. Cost estimates treat ordinary input, cache reads and cache writes as separate counts: `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` is total input, not three overlapping fields. Current5-minute writes use 1.25× input rate; reads 0.1×. Rates in code are configured estimates, not provider invoices or a current pricing guarantee. No 1-hour TTL is requested or priced by this helper. [Anthropic usage semantics](https://platform.claude.com/docs/en/build-with-claude/prompt-caching).

The returned usage log does not aggregate every failed repair/transient attempt. It has a cache-read count but no separate persisted cache-write count column; the successful-call estimated cost includes writes. Do not claim exact total session billing.

## Validation

Offline tests: `backend/tests/test_portfolio_regressions.py`, `backend/tests/test_scorer_utils.py`, `backend/tests/scoring/test_golden_answers.py`. These use synthetic inputs/mocked providers unless explicitly marked integration/nightly. Desired variance, parse-success, cache-hit and latency thresholds are targets, not measured results. No reproducible current live calibration is asserted. See [evals](../evals.md).
