#!/usr/bin/env bash
# run_demo.sh — Start InterviewCraft in offline demo mode.
#
# Usage:
#   ./scripts/run_demo.sh
#
# What it does:
#   1. Starts Postgres + Redis via docker compose
#   2. Runs Alembic migrations
#   3. Seeds the demo user with 10 pre-built sessions
#   4. Starts the backend + frontend
#
# After this runs, open http://localhost:3000
# Log in with: demo@interviewcraft.dev / demo1234
#
# Note: Voice sessions require real API keys (ANTHROPIC_API_KEY, DEEPGRAM_API_KEY,
#       ELEVENLABS_API_KEY). Without them, you can still browse all history,
#       skill graph, stories, negotiation, dashboard, and admin metrics.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Starting database services..."
docker compose up -d postgres redis

echo "==> Waiting for Postgres to be ready..."
until docker compose exec -T postgres pg_isready -U interviewcraft -q; do
  sleep 1
done

echo "==> Running migrations..."
docker compose run --rm backend alembic upgrade head

echo "==> Seeding demo data..."
docker compose run --rm backend python /app/scripts/seed_demo.py

echo "==> Starting all services..."
docker compose up -d backend frontend

echo ""
echo "✅ InterviewCraft demo is running!"
echo ""
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8080/api/docs"
echo ""
echo "   Demo login: demo@interviewcraft.dev / demo1234"
echo ""
echo "   To stop: docker compose down"
