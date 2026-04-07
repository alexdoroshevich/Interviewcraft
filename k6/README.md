# InterviewCraft Load Tests (k6)

Measures real p50/p95/p99 latency under load for all critical API paths.

## Prerequisites

```bash
# Install k6 (https://k6.io/docs/get-started/installation/)
# macOS
brew install k6
# Windows (scoop)
scoop add bucket https://github.com/grafana/scoop-k6
scoop install k6
```

## Usage

```bash
# Start backend first
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8080

# Run smoke test (quick sanity check, 1 VU, 30s)
k6 run --env BASE_URL=http://localhost:8080 k6/smoke.js

# Run baseline load test (10 VUs, 2 min) — get p50/p95/p99
k6 run --env BASE_URL=http://localhost:8080 k6/load.js

# Run spike test (burst to 50 VUs)
k6 run --env BASE_URL=http://localhost:8080 k6/spike.js

# Output JSON results for CI
k6 run --env BASE_URL=http://localhost:8080 --out json=k6/results.json k6/load.js
```

## Thresholds (what "passing" means)

| Metric | Target |
|--------|--------|
| `http_req_duration` p50 | < 200ms |
| `http_req_duration` p95 | < 800ms |
| `http_req_duration` p99 | < 2000ms |
| `http_req_failed` | < 1% |

## Test files

| File | Purpose |
|------|---------|
| `smoke.js` | 1 VU, 30s — sanity check all endpoints respond |
| `load.js` | 10 VUs, 2 min — baseline latency with real p50/p95/p99 |
| `spike.js` | ramps to 50 VUs — finds breaking points |
| `helpers.js` | Shared auth, setup, teardown helpers |
