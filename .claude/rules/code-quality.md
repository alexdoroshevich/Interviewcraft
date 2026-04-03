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

## Git — MANDATORY WORKFLOW
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`
- Commit after every working feature — not after hours of accumulated work
- No single commit with 500+ changed lines — split into smaller commits
- Never commit `.env`, API keys, or secrets
- **Never push directly to `main` or `master`** — no exceptions, not even for hotfixes
- **Required flow: feature branch → commit → push branch → PR → all CI checks green → merge**
- The branch guard hook enforces this at the tool level — do not attempt to bypass it
- Hook safety: the branch guard grep must be conditional (anchored `^git\s+push`) — never unconditional deny

## Pre-push Verification — MANDATORY
**Never push changes that will produce visible failures in GitHub CI.** Before every `git push`, verify:

1. **YAML syntax** — validate every new/modified `.github/workflows/*.yml` with:
   `python -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" <file>`
   A syntax error silently breaks the entire workflow.

2. **Action API compatibility** — when using `some-action@version`, verify input field names match that exact version. `@beta` vs `@v1` field names differ (e.g. `direct_prompt` → `prompt`, `model` → `claude_args`). Check the action's README.

3. **Conflict pre-check** — before pushing a branch that touches files also on another open branch or recently merged to main, run:
   `git fetch origin && git diff origin/main -- <file>` to surface conflicts before they become GitHub merge conflicts.

4. **File path correctness** — trace every path in workflows: `working-directory` + relative config path must resolve to a real file in the repo. Check `fly.toml`, `vercel.json`, `pyproject.toml` locations explicitly.

5. **Build output alignment** — if changing anything that affects build output location (next.config.mjs `output` mode, Dockerfile paths, Vercel settings), verify the deployment system will find the output at the new location.

6. **New workflow dry-run** — for any new workflow file, mentally simulate a full run: trigger event → permissions → steps → expected output. If it's a reviewer/bot action, verify it has the correct tool permissions and won't hit turn limits.

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
