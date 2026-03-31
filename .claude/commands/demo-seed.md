# /demo-seed — Seed realistic demo data for the live demo

Creates a demo user account with realistic sessions, scores, skill graph, and stories
so the live demo URL shows a fully-populated dashboard instead of empty state.

## Steps

1. Check if demo user exists:
```bash
docker compose exec postgres psql -U postgres -d interviewcraft -c \
  "SELECT id, email FROM users WHERE email = 'demo@interviewcraft.app';" 2>&1
```

2. If not exists, create via the API:
```bash
curl -s -X POST http://localhost:8080/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@interviewcraft.app","password":"Demo2026!","name":"Demo User"}' | jq .
```

3. Run the seed script (if it exists at backend/scripts/seed_demo.py):
```bash
docker compose exec backend python scripts/seed_demo.py 2>&1
```

4. Report: demo login credentials and what data was seeded.

Note: if seed_demo.py doesn't exist, tell the user we need to create it first.
