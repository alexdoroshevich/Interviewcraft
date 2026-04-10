# InterviewCraft

> **Deliberate practice engine for tech interviews.**
> Evidence-based scoring · answer diff rewriting · rewind micro-practice · 22-skill graph · salary negotiation simulator

[![Backend CI](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/frontend-ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## What Is This?

InterviewCraft is a **closed-loop training system** — not another mock interview tool. Like a sports coach who records every rep, identifies exactly what broke down, and makes you practice that specific thing until it's solid.

```
ANSWER → LINT (evidence spans) → DIFF (3 versions) → REWIND (re-answer)
    ↑       → DELTA SCORE → SKILL GRAPH UPDATE → ADAPTIVE DRILL PLAN ──┘
```

Every session feeds back into a persistent 22-microskill graph. The system knows which skills are weakest, schedules spaced-repetition drills, and tracks your delta across sessions — not just a one-shot score.

---

## Key Features

| Feature | What it does |
|---------|-------------|
| **Evidence-backed scoring** | 15-rule rubric. Every triggered rule links to `{start_ms, end_ms}` — the exact moment you said it. No hallucinated quotes. |
| **Answer diff (3 versions)** | Minimal patch · medium rewrite · ideal answer. Each shows `[+rule → +N points]`. |
| **Rewind micro-practice** | Re-answer any weak segment. Delta shown immediately: `+12 structure, -3 depth`. |
| **22-skill graph** | Microskills tracked across all sessions with trend lines and spaced-repetition scheduling. |
| **Cross-session AI memory** | The interviewer AI remembers your patterns across sessions — recurring weaknesses, over-used stories, communication habits. |
| **Story bank** | Auto-detects STAR stories. Coverage map shows which competencies lack evidence. Overuse warning after 3 uses. |
| **Negotiation simulator** | AI recruiter with hidden max budget. Scores anchoring, value articulation, counter-strategy, emotional control. |
| **JD Analyzer** | Paste a job description — auto-fills session type, company context, and focus skills. |
| **Voice delivery analysis** | Filler words, WPM, pause patterns — scored against benchmarks after each session. |
| **BYOK** | Use your own Anthropic / OpenAI / Deepgram / ElevenLabs keys. Encrypted at rest. |

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Backend | FastAPI + Python 3.13 | Async-native, fully typed, fast iteration |
| Frontend | Next.js 15 + Tailwind + Zustand | App Router, edge CDN, zero-config deploys |
| Voice | Deepgram Nova-2 + Claude Sonnet + ElevenLabs | Best-in-class STT/LLM/TTS with fallback chain |
| Database | PostgreSQL 16 + JSONB skill graph | Flexible schema, prompt-cached rubric reads |
| Cache | Redis 7 | Session state + rate limiting + memory cache |
| AI scoring | Anthropic Claude with prompt caching | Rubric cached = ~90% cheaper on re-reads |

---

## Architecture

```
                  GitHub (push to branch)
                         │
            ┌────────────┴────────────┐
            │                         │
       Fly.io (Backend)         Vercel (Frontend)
       FastAPI + Python          Next.js + React
       WebSocket voice           SSR + Edge CDN
       PostgreSQL + Redis        Auto HTTPS
       Long-lived processes      Zero config
            │                         │
            └────────────┬────────────┘
                         │
                User visits website
                Frontend → NEXT_PUBLIC_API_URL
```

**Why split?** Vercel cannot run WebSocket connections or long-lived processes (voice sessions need 30+ minute connections). Fly.io handles the stateful backend; Vercel handles the CDN-optimised frontend.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.13+, Node.js 20+
- API keys: `ANTHROPIC_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`

### Run locally

```bash
git clone https://github.com/alexdoroshevich/interviewcraft.git
cd interviewcraft

cp .env.example .env
# Edit .env — add your API keys

# Start all services: postgres, redis, backend, frontend
docker compose up -d

# First run: apply DB migrations
cd backend && pip install -e ".[dev]" && alembic upgrade head
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8080/api/docs

### Seed demo data

```bash
cd backend && python ../scripts/seed_demo.py
```

Loads 10 pre-built sessions, a skill graph, story bank, and negotiation history. Demo login: `demo@interviewcraft.dev` / `demo1234`

---

## Google Authentication

The "Continue with Google" button activates automatically once `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set:

1. [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → Create OAuth 2.0 Client ID (Web application)
2. Authorized Origins: `http://localhost:3000` + your production domain
3. Authorized Redirect URI: `http://localhost:8080/api/v1/auth/google/callback`
4. Add to `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id
   ```

---

## Development

```bash
# Backend tests
cd backend && pytest -x -q

# Backend lint + type check
cd backend && ruff check . && mypy app/

# Frontend
cd frontend && npm run lint && npm run type-check && npm test

# E2E tests (requires running app)
cd frontend && npm run test:e2e
```

All PRs run these automatically via GitHub Actions. A PR cannot merge unless every gate passes.

---

## Deployment

The backend deploys to [Fly.io](https://fly.io) and the frontend to [Vercel](https://vercel.com).

**Frontend (Vercel):** Import the repo, set Root Directory to `frontend`, add `NEXT_PUBLIC_API_URL` pointing to your Fly.io backend. Every push auto-deploys; every PR gets a preview URL.

**Backend (Fly.io):**
```bash
flyctl auth login
flyctl apps create <your-app-name>
flyctl postgres create --name <your-db> && flyctl postgres attach <your-db>
flyctl secrets set ANTHROPIC_API_KEY="..." DEEPGRAM_API_KEY="..." # see .env.example
flyctl deploy --config backend/fly.toml
```

After the initial deploy, GitHub Actions handles all subsequent deploys automatically on push to `main`.

---

## Database Migrations

```bash
# Apply all pending migrations (local)
cd backend && alembic upgrade head

# Apply on Fly.io
flyctl ssh console --app <your-app-name>
cd /app && python -m alembic upgrade head

# Create a new migration after model changes
cd backend && alembic revision --autogenerate -m "description"
```

---

## Daily Workflow

```bash
# 1. Create a feature branch from main
git checkout main && git pull
git checkout -b feature/my-feature

# 2. Make changes, commit
git commit -m "feat: my feature"
git push origin feature/my-feature

# 3. Open a PR → CI runs automatically
#    All gates must pass before merging

# 4. Merge → auto-deploys to production
```

---

## Project Structure

```
interviewcraft/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (auth, sessions, scoring, skills…)
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── services/        # Voice pipeline, scoring engine, memory, auth
│   └── tests/               # Unit + integration tests
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # Shared React components
│   └── lib/api.ts           # Typed API client
├── docs/
│   └── adr/                 # Architecture Decision Records
└── scripts/
    ├── seed_demo.py         # Demo data
    └── run_demo.sh          # One-command demo startup
```

---

## Architecture Decisions

Key decisions are documented in [`docs/adr/`](docs/adr/):

| ADR | Decision |
|-----|---------|
| [000](docs/adr/000-north-star-spec.md) | North Star specification |
| [001](docs/adr/001-websocket-vs-webrtc.md) | WebSocket over WebRTC for voice |
| [002](docs/adr/002-tech-stack.md) | Full tech stack rationale |
| [003](docs/adr/003-scoring-architecture.md) | Evidence spans + batched scoring |
| [004](docs/adr/004-rewind-segmentation.md) | Text-only rewind in MVP |
| [005](docs/adr/005-provider-abstractions.md) | Provider ABC interfaces |
| [006](docs/adr/006-privacy-data-retention.md) | Audio never stored, encrypted transcripts |
| [007](docs/adr/007-swe-only-mvp.md) | SWE-only scope, extensible architecture |
| [008](docs/adr/008-scoring-stability.md) | Four-technique variance reduction |

---

## Benchmarks

The [`benchmarks/`](benchmarks/) directory contains reproducible evaluations of the system's AI subsystems. All scripts require a valid Anthropic API key and run against the real model APIs. Dated output files are gitignored — only synthetic `example.json` baselines are committed.

| Benchmark | What it measures | KPI |
|-----------|-----------------|-----|
| [memory-recall](benchmarks/memory-recall/) | Does the LLM accurately recall injected coaching context? | ≥ 95% recall, 0% hallucination |
| [scoring-quality](benchmarks/scoring-quality/) | Do automated scores correlate with human judgement? | Pearson r ≥ 0.85, MAE ≤ 10 |
| [voice-latency](benchmarks/voice-latency/) | STT → LLM → TTS latency (mock + production) | E2E p95 < 1 000 ms |
| [cost-profile](benchmarks/cost-profile/) | Cost per session by quality profile and provider | — |

Run any benchmark with `--confirm` to execute live API calls (see each README for cost estimates). Use the mock scripts to explore latency characteristics without any API keys.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
