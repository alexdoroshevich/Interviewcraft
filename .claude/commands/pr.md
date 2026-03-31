# /pr — Create a pull request with auto-generated description

Creates a PR from the current branch into main with a description generated from the commit log.

## Steps

1. Get the current branch name and commits since main:
```bash
git branch --show-current
git log main..HEAD --oneline
git diff main..HEAD --stat | tail -5
```

2. Based on the commits and changed files, write a PR title and description in this format:
   - Title: short (under 70 chars), conventional commit style: `feat:`, `fix:`, `chore:` etc.
   - Body: use the template below

3. Create the PR:
```bash
gh pr create \
  --base main \
  --title "<generated title>" \
  --body "<generated body>"
```

## PR body template

```markdown
## What does this PR do?
<1-3 bullet points summarizing the changes>

## Why?
<motivation — bug fix, feature request, deployment prep, etc.>

## Checklist
- [ ] Backend tests pass (`cd backend && pytest -x -q`)
- [ ] Frontend builds (`cd frontend && npm run build`)
- [ ] No secrets or PII committed
- [ ] Migrations applied if schema changed

## How to test
<steps to verify the changes work>
```

## Notes
- After running, GitHub will print the PR URL — open it to verify
- If status checks fail, fix them and push — the PR updates automatically
- Claude reviewer will post a review automatically within ~30 seconds of PR creation
