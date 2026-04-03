# InterviewCraft

> **Deliberate practice engine for tech interviews.**
> Evidence-based scoring · git-diff answer rewriting · rewind micro-practice · 22-skill graph memory · salary negotiation simulator

[![Backend CI](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/backend-ci.yml/badge.svg)](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/backend-ci.yml)
[![Frontend CI](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/frontend-ci.yml/badge.svg)](https://github.com/alexdoroshevich/interviewcraft/actions/workflows/frontend-ci.yml)
[![Tests](https://img.shields.io/badge/tests-156%20passed-brightgreen)](backend/tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---

## What Is This?

InterviewCraft is NOT "another AI mock interview tool." It's a **closed-loop training system** — like a sports coach who records every rep, identifies what broke down, and makes you practice that exact thing until it's solid.

```
ANSWER → LINT (evidence spans) → DIFF (3 versions) → REWIND (re-answer)
    ↑       → DELTA SCORE → SKILL GRAPH UPDATE → ADAPTIVE DRILL PLAN ──┘
```

### The key differentiators

| Feature | What it does |
|---|---|
| **Evidence-backed scoring** | 15-rule rubric. Every triggered rule links to `{start_ms, end_ms}` — the exact moment you said it. No hallucinated quotes. |
| **Answer diff (3 versions)** | Minimal patch / medium rewrite / ideal answer. Each annotation shows `[+rule → +N points]`. |
| **Rewind micro-practice** | Re-answer any weak segment. Delta shown immediately: `+12 structure, -3 depth`. |
| **Skill graph memory** | 22 microskills tracked across all sessions. Spaced repetition schedules your weakest areas. |
| **Story bank** | Auto-detects STAR stories. Coverage map shows which competencies lack evidence. Overuse warning after 3 uses. |
| **Negotiation simulator** | AI recruiter with hidden max budget (offer × 1.15). Scores anchoring, value articulation, counter-strategy, emotional control. |
| **Admin metrics** | Real-time latency p50/p95, cache hit rate, scoring variance — all DoD KPIs on one page. |

---

## Demo

```bash
# One command — no API keys needed for browsing
./scripts/run_demo.sh
```

Opens at `http://localhost:3000`. Log in: `demo@interviewcraft.dev` / `demo1234`

Includes 10 pre-built sessions, skill graph, story bank, and negotiation history.

> Voice sessions require Anthropic + Deepgram + ElevenLabs API keys.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend | FastAPI + Python 3.13 | Async, fast, typed |
| Frontend | Next.js 15 + App Router + Tailwind | App Router for layouts |
| Voice | Pipecat + Deepgram Nova-2 + Claude Sonnet + ElevenLabs | Open-source orchestration |
| Database | PostgreSQL 16 (JSONB skill graph) | Flexible schema, no migrations for new skills |
| Cache | Redis 7 | Rate limiting + session state |
| AI scoring | Anthropic Claude with prompt caching | Rubric cached = 90% cheaper re-reads |

See [`docs/adr/`](docs/adr/) for all architectural decisions.

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Python 3.13+, Node.js 20+
- API keys: `ANTHROPIC_API_KEY`, `DEEPGRAM_API_KEY`, `ELEVENLABS_API_KEY`

### Setup

```bash
git clone https://github.com/alexdoroshevich/interviewcraft.git
cd interviewcraft
cp .env.example .env
# Edit .env — add your API keys

# Start all services (postgres, redis, chromadb, backend, frontend)
docker compose up -d

# First run: apply DB migrations
cd backend && pip install -e ".[dev]" && alembic upgrade head
```

- Frontend: http://localhost:3000
- API docs: http://localhost:8080/api/docs
- Admin metrics: http://localhost:3000/admin/metrics

### Seed demo data

```bash
cd backend && python ../scripts/seed_demo.py
```

---

## Google Authentication

The **"Continue with Google"** button appears on the login page automatically once `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set. Steps to enable it:

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Web application)
3. Add Authorized Origins: `http://localhost:3000` (dev) + your production domain
4. Add Authorized Redirect URIs: `http://localhost:8080/api/v1/auth/google/callback`
5. Set in `.env`:
   ```env
   GOOGLE_CLIENT_ID=your-client-id
   GOOGLE_CLIENT_SECRET=your-client-secret
   NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id   # same value
   ```

---

## Cost model

This is an open-source portfolio project, not a commercial product.

| What | Who pays |
|------|---------|
| Hosting (Vercel + Fly.io) | Project author |
| Deepgram STT | Project author (small per-session cost) |
| ElevenLabs TTS | Project author (small per-session cost) |
| **Anthropic (Claude)** | **You — bring your own key after the first session** |

**Your first session is completely free.** After that, add your own Anthropic API key in Settings.
Get one free at [console.anthropic.com](https://console.anthropic.com). Claude costs roughly $0.30–1.30 per session depending on the quality profile you choose.

---

## Multi-Model Support (BYOK)

Go to **Settings → Bring Your Own Keys** to use your own API keys. Supported providers:

| Provider | Effect |
|---|---|
| **Anthropic (Claude)** | Required from session 2 onwards. Uses your key for all Claude calls. |
| **OpenAI (GPT-4o)** | Optional. Replaces Claude entirely — GPT-4o for quality/balanced, GPT-4o-mini for budget. |
| **Deepgram** | Optional. Uses your key for speech-to-text. |
| **ElevenLabs** | Optional. Uses your key for text-to-speech. |

Keys are encrypted at rest (Fernet AES-128-CBC + HMAC) and never appear in logs.

---

## Branch Strategy & Workflow

```
main       ──▶  production (auto-deploy on push, requires owner approval)
stage      ──▶  staging    (auto-deploy on push, used for pre-release QA)
dev        ──▶  dev env    (auto-deploy on push, used for active development)
feature/*  ──▶  open PRs against dev (or stage for ready features)
hotfix/*   ──▶  open PRs directly against main
```

**Typical feature flow:**

```bash
# 1. Branch from dev
git checkout dev && git pull origin dev
git checkout -b feature/my-feature

# 2. Develop + commit
git add -p
git commit -m "feat: my feature"
git push origin feature/my-feature

# 3. Open PR → dev
#    pr-gate.yml runs automatically:
#      - ruff + mypy (backend)
#      - eslint + tsc + vitest (frontend)
#      - PR description length check
#    ALL must pass + owner approval required before merge

# 4. Merge → auto-deploys to dev environment for testing

# 5. When ready for release: open PR dev → stage
#    Same gate runs. Merge → deploys to staging for QA.

# 6. After QA sign-off: open PR stage → main
#    Merge → deploys to production.
```

**Branch protection settings to configure in GitHub** (Settings → Branches → Add rule):

| Branch | Settings |
|--------|---------|
| `main` | Require PR, 1 approval, require Code Owners review, require `all-gates-passed` status check, no bypass |
| `stage` | Require PR, 1 approval, require Code Owners review, require `all-gates-passed` status check |
| `dev` | Require PR, require `all-gates-passed` status check (no approval required) |

---

## CI/CD Pipeline

### Quality gates (run on every PR)

**`pr-gate.yml`** — must pass before any PR can be merged:

| Gate | What it checks |
|------|---------------|
| Backend gate | `ruff check` + `mypy app/` + `pytest --cov-fail-under=70` |
| Frontend gate | `eslint` + `tsc` + `vitest` |
| Pre-commit hooks | trailing whitespace, YAML/TOML/JSON validity, secret detection (gitleaks) |
| PR description | Must be >= 50 chars (fill the template) |
| Commit messages | Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, etc. |
| PR title | Semantic format: `feat: add X`, `fix: resolve Y` |

### CI pipelines (run on push to `dev`, `stage`, `main`)

| Workflow | Scope |
|----------|-------|
| `backend-ci.yml` | ruff + mypy + pytest (unit tests) |
| `frontend-ci.yml` | eslint + tsc + vitest + Playwright E2E |
| `bandit.yml` | Python SAST security scan (severity: high) |

### Auto-deploy (run on push to `dev`, `stage`, `main`)

**`deploy.yml`** runs the full test suite, then deploys:

| Branch | Backend target (Fly.io) | Frontend target (Vercel) | Secrets needed |
|--------|------------------------|-------------------------|----------------|
| `dev` | Dev Fly.io app | Preview deployment (auto) | `FLY_API_TOKEN_DEV` |
| `stage` | Staging Fly.io app | Preview deployment (auto) | `FLY_API_TOKEN_STAGING` |
| `main` | Production Fly.io app | Production (auto) | `FLY_API_TOKEN` |

Manual deploys available via **GitHub -> Actions -> Deploy -> Run workflow**.

---

## Deployment Architecture

The app is split across two hosting providers because they serve different needs:

```
                    GitHub (push to branch)
                           |
              +------------+------------+
              |                         |
         Fly.io (Backend)        Vercel (Frontend)
         - FastAPI + Python      - Next.js + React
         - WebSocket voice       - SSR + Edge CDN
         - PostgreSQL + Redis    - Auto HTTPS
         - Long-lived processes  - Zero config
              |                         |
              +------------+------------+
                           |
                  User visits website
                  Frontend calls API at
                  NEXT_PUBLIC_API_URL
```

**Why not all on one provider?**
- Vercel cannot run WebSocket connections or long-lived processes (voice pipeline needs 30+ minute connections)
- Fly.io can run everything but has no CDN, no edge SSR, and is more expensive for static assets
- This split is the industry standard for Next.js + Python API projects

---

## Deployment

The app deploys to **Fly.io** (backend) and **Vercel** (frontend). See the architecture diagram above for the split rationale.

### One-time setup

**Frontend (Vercel):**
1. Import the repo on [vercel.com](https://vercel.com) — set Root Directory to `frontend`
2. Add environment variable: `NEXT_PUBLIC_API_URL=https://<your-fly-app>.fly.dev`
3. Every push to `main` auto-deploys. Every PR gets a preview URL.

**Backend (Fly.io):**
```bash
# Install flyctl: https://fly.io/docs/hands-on/install-flyctl/
flyctl auth login

# Create apps for each environment (dev / staging / production)
flyctl apps create <your-app-dev>
flyctl apps create <your-app-staging>
flyctl apps create <your-app>

# Create and attach a Postgres database
flyctl postgres create --name <your-db>
flyctl postgres attach <your-db> --app <your-app>

# Set required secrets (see .env.example for the full list)
flyctl secrets set \
  SECRET_KEY="$(openssl rand -hex 32)" \
  JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  ANTHROPIC_API_KEY="sk-ant-..." \
  DEEPGRAM_API_KEY="..." \
  ELEVENLABS_API_KEY="..." \
  REDIS_URL="redis://..." \
  --app <your-app>

# Initial deploy — subsequent deploys run automatically via GitHub Actions
flyctl deploy --config backend/fly.toml
```

**GitHub Secrets** (Settings → Secrets and variables → Actions):

| Secret | Value |
|--------|-------|
| `FLY_API_TOKEN` | `flyctl tokens create deploy --app <your-app>` |
| `FLY_API_TOKEN_STAGING` | `flyctl tokens create deploy --app <your-app-staging>` |
| `FLY_API_TOKEN_DEV` | `flyctl tokens create deploy --app <your-app-dev>` |

**Run database migrations:**
```bash
flyctl ssh console --app <your-app>
cd /app && python -m alembic upgrade head
```

### Daily workflow

After setup, you never run deploy commands manually:

```bash
git checkout -b feature/my-feature
# ... make changes ...
git commit -m "feat: my feature"
git push origin feature/my-feature
# Open PR → CI gates run → merge → auto-deploys
```

---

## Resume / Document Storage

When you upload a resume (PDF/DOCX), this is what happens:

1. File is read into memory (max 5 MB)
2. Text is extracted using PyPDF2 (PDF) or python-docx (DOCX)
3. Claude Haiku parses the text into structured JSON (skills, experience, projects)
4. **Structured profile is stored in PostgreSQL** (`users.profile` JSONB column)
5. **Raw resume text is stored in PostgreSQL** (`users.resume_text`, up to 50k chars)
6. **The original PDF/DOCX file is discarded** — it is not stored anywhere

To re-parse a resume, the user must upload the file again. This is by design — no file storage costs, no PII in blob storage, GDPR-friendly.

---

## Development

```bash
# Backend tests (excludes integration + nightly)
cd backend && pytest -x -q -m "not integration and not nightly"

# Backend lint + type check
cd backend && ruff check . && mypy app/

# Frontend
cd frontend && npm run lint && npm run type-check

# E2E tests (requires running app + demo data)
cd frontend && npm run test:e2e
```

---

## Project Structure

```
interviewcraft/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # Route handlers (auth, sessions, scoring, skills, ...)
│   │   ├── models/          # SQLAlchemy models
│   │   ├── schemas/         # Pydantic schemas
│   │   └── services/        # Voice pipeline, scoring engine, memory, auth
│   └── tests/               # 156 tests (unit + integration)
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # Shared React components
│   ├── e2e/                 # Playwright E2E tests
│   └── lib/api.ts           # Typed API client
├── docs/
│   ├── adr/                 # 9 Architecture Decision Records
│   ├── devlog/              # Weekly development logs
│   ├── runbook.md           # Operations guide
│   ├── failure-modes.md     # Degradation strategies
│   ├── security.md          # Threat model + encryption
│   └── evals.md             # Scoring evaluation methodology
└── scripts/
    ├── seed_demo.py         # Creates demo user with realistic data
    ├── seed_questions.py    # Seeds 50 SWE questions
    └── run_demo.sh          # One-command demo startup
```

---

## Definition of Done

All 8 KPIs tracked live at `/admin/metrics`:

| KPI | Target | Status |
|---|---|---|
| Voice latency p95 | < 1000ms | Monitored |
| Scoring variance | < 8 pts (golden set) | Calibrated: avg 4.1 |
| JSON parse fail rate | < 5% | < 2% in testing |
| Rewind delta avg | > +10 pts | Architecture supports |
| Cost per session | Shown in UI | Dashboard + usage_logs |
| Cache hit rate | > 70% | Monitored |
| Offline demo | Works without API keys | `run_demo.sh` |
| Dogfooding | 10+ sessions | In progress |

---

## Architecture Decisions

| ADR | Decision |
|---|---|
| [000](docs/adr/000-north-star-spec.md) | North Star specification |
| [001](docs/adr/001-websocket-vs-webrtc.md) | WebSocket over WebRTC for voice |
| [002](docs/adr/002-tech-stack.md) | Full tech stack rationale |
| [003](docs/adr/003-scoring-architecture.md) | Evidence spans + batched scoring |
| [004](docs/adr/004-rewind-segmentation.md) | Text-only rewind in MVP |
| [005](docs/adr/005-provider-abstractions.md) | Provider ABC interfaces |
| [006](docs/adr/006-privacy-data-retention.md) | Audio never stored, AES-256 transcripts |
| [007](docs/adr/007-swe-only-mvp.md) | SWE-only scope, extensible architecture |
| [008](docs/adr/008-scoring-stability.md) | Four-technique variance reduction |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please read it before opening a PR.

## License

[MIT](LICENSE)
