# Synthetic-profile memory recall evaluation

`run.py` formats synthetic profile documents using the application's memory formatter and can ask the configured Anthropic model questions about that context. It does not create two persisted sessions or validate the complete PostgreSQL/Redis/background-builder path. Its purpose-built inputs are not real user observations.

From repository root, only with an approved budget/key:

```sh
python benchmarks/memory-recall/run.py --confirm
```

Inspect script prompts, case count, model and price assumptions before use. Keep raw output and source/model/configuration alongside any metric. The committed `results/example.json` is a synthetic format example; no current 95% recall/0% hallucination result is claimed. The separate historical `backend/scripts/memory_benchmark_results.json`, if consulted, is not automatically a run of this script or evidence for the current source. [Interpretation and conditions](../../docs/evals.md).
