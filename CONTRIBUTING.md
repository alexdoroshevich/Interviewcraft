# Contributing to InterviewCraft

Thanks for your interest! InterviewCraft is a portfolio project with a strict scope
(see ADR-007: SWE-Only MVP). Before contributing, please read this document.

---

## Before You Start

1. **Check the scope.** Features not in the spec will not be merged. See `HANDOFF.md` and `docs/adr/007-swe-only-mvp.md`.
2. **Check existing issues.** Search open issues before opening a new one.
3. **For significant changes:** Open an issue first to discuss the approach.

---

## Development Setup

```bash
# Clone
git clone https://github.com/YOUR_HANDLE/interviewcraft.git
cd interviewcraft

# Backend
cd backend
cp .env.example .env        # fill in your API keys
pip install -e ".[dev]"
alembic upgrade head

# Frontend
cd ../frontend
npm install
npm run dev

# Or: start everything with Docker
docker compose up
```

### Required API keys (for voice sessions)
- `ANTHROPIC_API_KEY` — Claude Sonnet/Haiku
- `DEEPGRAM_API_KEY` — Nova-2 STT
- `ELEVENLABS_API_KEY` — TTS (or use Deepgram Aura-1 for budget)

**Demo mode** (no API keys needed):
```bash
./scripts/run_demo.sh
```

---

## Code Standards

### Python (backend)
- **Type hints on ALL functions.** `mypy --strict` must pass.
- **Docstrings on all public functions** (one-line minimum).
- **`structlog` for all logging.** Never `print()`. Never log PII.
- **`pytest -x -q` must pass** before opening a PR.
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`

### TypeScript (frontend)
- **Strict mode on.** No `any` types.
- `tsc --noEmit` must pass.
- `eslint` must pass with no errors.

### Tests
- Every new backend file needs at minimum a smoke test.
- Golden answer tests: don't change `golden_answers.json` without calibration evidence.
- Mark integration tests with `@pytest.mark.integration` — they're excluded from CI by default.

---

## Pull Request Process

1. Fork the repo, create a branch: `feat/your-feature-name`
2. Make your changes + tests
3. Run `pytest -x -q -m "not integration and not nightly"` (backend)
4. Run `npm run type-check && npm run lint` (frontend)
5. Open a PR with:
   - What problem it solves
   - Which spec section it implements (if applicable)
   - Test results screenshot or log

### PR review criteria
- [ ] Tests pass
- [ ] No `any` types introduced
- [ ] No PII logged
- [ ] Follows existing patterns (DI, error handling, structlog)
- [ ] Spec-aligned (no out-of-scope features)

---

## Good First Issues

Look for issues labeled `good first issue`. These are:
- Improving error messages
- Adding missing tests for existing code
- Documentation improvements
- Seed question bank additions (behavioral questions)

---

## What We Won't Accept

- Features not in the MVP spec (BYOK, multiple professions, billing, video)
- Stack changes (FastAPI → Django, Next.js → Remix, etc.)
- Audio storage (ADR-006: privacy decision, not negotiable)
- `console.log()` or `print()` debugging statements left in code
- Commits with `.env` files or API keys

---

## Questions?

Open a GitHub Discussion. For architecture questions, reference the relevant ADR first.
