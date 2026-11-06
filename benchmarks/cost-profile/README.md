# Usage-log cost estimates

From repository root with access to an existing database and DATABASE_URL configured:

```sh
python benchmarks/cost-profile/query.py
```

This script aggregates saved `usage_logs`; it does not invoke model/audio APIs. `cost_usd` is a configured-rate estimate, not a provider invoice. The corrected Anthropic helper prices disjoint ordinary input, cache reads and 5-minute cache writes. No 1-hour write TTL is configured. Successful-call estimates include writes, but cache-write token counts have no dedicated persisted column; failed/repaired attempts and provider-neutral routing are not fully reconciled. Do not claim every billed call or exact session cost is captured.

`results/example.json` is synthetic. Previously listed session prices, 71.2% cache-hit rate and 70% savings are not retained as measured results without raw provenance/conditions. Cache eligibility/hits and generation variability are separate; a cache does not guarantee all requests hit or all outputs match. [Evaluation methodology](../../docs/evals.md).
