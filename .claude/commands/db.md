# /db — Inspect database state

Quick database inspection — counts, recent records, migration status.

## Steps

1. Migration status:
```bash
docker compose exec backend alembic current 2>&1
```

2. Row counts for key tables:
```bash
docker compose exec postgres psql -U interviewcraft -d interviewcraft -c "
SELECT
  (SELECT COUNT(*) FROM users) AS users,
  (SELECT COUNT(*) FROM sessions) AS sessions,
  (SELECT COUNT(*) FROM session_segments) AS segments,
  (SELECT COUNT(*) FROM skill_nodes) AS skill_nodes,
  (SELECT COUNT(*) FROM questions) AS questions,
  (SELECT COUNT(*) FROM stories) AS stories,
  (SELECT COUNT(*) FROM usage_logs) AS usage_logs;
" 2>&1
```

3. Recent sessions (last 5):
```bash
docker compose exec postgres psql -U interviewcraft -d interviewcraft -c "
SELECT id, type, status, quality_profile, company, created_at
FROM sessions ORDER BY created_at DESC LIMIT 5;
" 2>&1
```

4. Total API cost:
```bash
docker compose exec postgres psql -U interviewcraft -d interviewcraft -c "
SELECT provider, operation, COUNT(*) as calls, SUM(cost_usd) as total_cost
FROM usage_logs GROUP BY provider, operation ORDER BY total_cost DESC;
" 2>&1
```

Report the results clearly. Flag anything unusual (0 questions, missing migrations, high cost).
