# Synthetic scoring-reference evaluation

`dataset.json` contains purpose-written Q&A and author-assigned reference scores/rules. These are not independently validated human judgments or objective hiring/readiness labels. `run.py` can compare real model output with those references using correlation, error and rule agreement. A good correlation alone would not establish assessment validity.

From repository root, only after approval of credentials and the call budget:

```sh
python benchmarks/scoring-quality/run.py --confirm
python benchmarks/scoring-quality/run.py --runs 3 --confirm
```

The script uses mocked persistence but real paid model calls. Review run count/retry behavior first. Committed `results/example.json` values are synthetic examples, not measured baseline r/MAE/precision/recall. No achieved score-quality metric is asserted here. Retain raw responses, failures, version/model/prompt information and evaluation conditions. [Methodology](../../docs/evals.md).
