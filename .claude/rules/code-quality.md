---
paths:
  - "backend/**/*.py"
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Code Quality Rules

## Python
- Type hints on **all** functions — parameters and return types
- Docstrings on all public functions (one-liner minimum)
- Use `structlog` for all logging — never `print()`
- Never swallow exceptions silently — always log or re-raise
- Never log PII, transcripts, user answers, or API keys
- Allowed log fields: `session_id`, `latency`, `cost`, `error`, `provider`, `model`

## TypeScript
- Strict mode always enabled
- No `any` types — use proper interfaces or `unknown` with type guards
- Tailwind for styling — no inline styles or CSS modules
- Zustand for state management — no prop drilling beyond 2 levels

## Testing
- Every new file needs at minimum a smoke test
- Golden answer tests: lite (10x3) in CI, full (30x5) nightly
- Run `pytest -x -q` before declaring Python work done
- Run `npx tsc --noEmit` before declaring TypeScript work done

## Dependencies
- Never install packages not in the approved list without asking
- Python pins: see `pyproject.toml` version constraints
- Critical pins: `deepgram-sdk>=4,<5`, `bcrypt>=3.2,<4`, `anthropic>=0.40,<1`
- Node: check `package.json` before adding anything

## Autonomous Operation — MANDATORY
- **Never ask permission** to run terminal commands, read files, explore directories/repos, fetch URLs, or use any tool
- Just do it — report results after, not before
- **Only ask before `git push`** — that is the single exception
- This applies to everything: bash, file edits, web searches, Docker, npm, migrations, other repos/folders

## Git
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`
- Commit after every working feature — not after hours of accumulated work
- No single commit with 500+ changed lines — split into smaller commits
- Never commit `.env`, API keys, or secrets

## Pull Requests — MANDATORY
- **NEVER open a PR with empty or placeholder template fields** — this has been corrected multiple times
- Every PR body must fill ALL fields in `.github/pull_request_template.md`:
  - "What does this PR do?" — specific paragraph about THIS change, not a title repeat
  - "Type of change" — check the correct boxes with `[x]`
  - "Checklist" — check every applicable item with `[x]`
  - "How to test" — numbered steps a reviewer can actually follow
  - "Related issues" — issue link or "N/A"
- Use `gh pr create --title "type: desc" --body "..."` to pre-fill body automatically
- If `gh` is unavailable, print the full filled-in body for the user to paste — never open empty
