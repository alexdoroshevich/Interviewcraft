# /readme — Regenerate the project README

Rewrites README.md to be compelling for both recruiters and senior engineers.
Covers: what it is, architecture diagram (text), tech stack, key engineering decisions, live demo link, local setup.

## Steps

1. Read the current README.md
2. Read CLAUDE.md for the full feature list and architecture
3. Read backend/app/main.py for route overview
4. Read backend/app/services/voice/pipeline.py lines 1-50 for pipeline description
5. Read frontend/app layout structure (list of pages)

Then rewrite README.md with these sections:
- **Hero** — one punchy sentence: what it is and why it's technically interesting
- **Live Demo** — link placeholder + screenshot placeholder
- **What makes it interesting** — 4-5 bullet engineering highlights (voice pipeline latency, scoring architecture, skill graph, etc.)
- **Architecture** — ASCII diagram of the full system
- **Tech Stack** — table with backend/frontend/AI/infra
- **Key Engineering Decisions** — link to docs/adr/ files
- **Local Setup** — copy from CLAUDE.md, clean up
- **Deployment** — Fly.io + Vercel

Write the result directly to README.md.
