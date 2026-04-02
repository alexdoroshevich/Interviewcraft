# /pr — Create a pull request with a fully filled description

Creates a PR from the current branch into main. ALWAYS fills in the description
using the project template — never leave fields empty or use placeholders.

## Steps

1. Gather context:
```bash
git branch --show-current
git log main..HEAD --oneline
git diff main..HEAD --stat
```

2. Read the PR template to get the exact structure:
```bash
cat .github/pull_request_template.md
```

3. Based on the commits and diff, write:
   - **Title**: under 70 chars, conventional commit format: `feat:`, `fix:`, `chore:`, `ci:`, etc.
   - **Body**: fill every section of the template with specific content about THIS change

4. Create the PR:
```bash
gh pr create \
  --base main \
  --title "<generated title>" \
  --body "$(cat <<'EOF'
<filled body here>
EOF
)"
```

## How to fill the body

Use the template sections exactly as they appear in `.github/pull_request_template.md`:

```markdown
## What does this PR do?

<One specific paragraph about what changed and why — not a title repeat>

## Type of change

- [x] Bug fix        ← check whichever apply
- [ ] New feature
- [ ] Refactor / cleanup
- [ ] Docs / config only
- [x] CI/CD

## Checklist (author)

- [x] I have read the relevant spec section / HANDOFF.md
- [x] Code follows the style guide (ruff / eslint pass locally)
- [x] Type hints on all Python functions; no TypeScript `any`
- [x] No `print()` or `console.log()` — using structlog / proper logger
- [x] No PII, transcripts, or API keys in logs or comments
- [ ] New files have at least a smoke test        ← uncheck if not applicable
- [x] `pytest -x -q -m "not integration"` passes locally
- [x] `npm run lint && npm run type-check` passes locally
- [x] No new packages added without discussion
- [x] Conventional commit prefix used (`feat:`, `fix:`, `chore:`, etc.)

## How to test

1. <Concrete first step a reviewer can follow>
2. <Second step>
3. <Expected result>

## Screenshots (if UI change)

<Before / After — or omit section if not a UI change>

## Related issues / spec sections

<Link to issue or "N/A">
```

## Rules

- Every field must be specific to THIS change — no generic placeholders
- Check boxes that apply with `[x]`, leave inapplicable ones unchecked `[ ]`
- If `gh` is not authenticated, run `gh auth login` first
- After creating the PR, print the URL so the user can open it
- The Claude reviewer will automatically post a review within ~60 seconds
