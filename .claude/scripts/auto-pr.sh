#!/usr/bin/env bash
# Auto-creates a GitHub PR after every `git push origin <branch>`.
# Fires as a PostToolUse hook on Bash. Reads hook JSON from stdin.
# Outputs a systemMessage JSON so Claude Code shows the PR URL in the UI.
# Silently exits on any error — never blocks the push.

set -euo pipefail

# ── Parse the bash command that was just run ─────────────────────────────────
input=$(cat)
cmd=$(python3 -c "
import sys, json
try:
    d = json.loads(sys.stdin.read())
    print(d.get('tool_input', {}).get('command', ''))
except:
    print('')
" <<< "$input" 2>/dev/null || echo "")

# Only trigger on: git push origin <branch>
echo "$cmd" | grep -qE "git push origin" || exit 0

# Extract branch name (first non-flag word after "origin")
branch=$(echo "$cmd" | grep -oP "(?<=git push origin )[\w/._-]+" | head -1 || echo "")
[[ -z "$branch" || "$branch" =~ ^(main|master|HEAD)$ ]] && exit 0

# Give GitHub a moment to register the push
sleep 2

# Resolve repo root and cd there
repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$repo_root"

# Skip if a PR already exists for this branch
gh pr view "$branch" --json number &>/dev/null 2>&1 && exit 0

# ── Build description from git log ───────────────────────────────────────────
commits=$(git log "origin/main..$branch" --format="- %s" 2>/dev/null | head -10)
[[ -z "$commits" ]] && commits="- See commit history for full details"

# Use the first commit subject as the PR title (conventional commit on the branch)
title=$(git log "origin/main..$branch" --format="%s" 2>/dev/null | tail -1)
[[ -z "$title" ]] && title="$branch"

# ── Detect what changed to auto-check relevant boxes ─────────────────────────
changed_files=$(git diff "origin/main..$branch" --name-only 2>/dev/null || echo "")

has_py=$(echo "$changed_files" | grep -c '\.py$' || true)
has_ts=$(echo "$changed_files" | grep -cE '\.(ts|tsx)$' || true)
has_migration=$(echo "$changed_files" | grep -c 'alembic/versions/' || true)
has_tests=$(echo "$changed_files" | grep -cE '(test_|\.test\.)' || true)
has_ci=$(echo "$changed_files" | grep -c '\.github/' || true)
has_docs=$(echo "$changed_files" | grep -cE '\.(md)$' || true)

# Detect change type for "Type of change" section
is_feat=$(echo "$title" | grep -c '^feat:' || true)
is_fix=$(echo "$title" | grep -c '^fix:' || true)
is_refactor=$(echo "$title" | grep -c '^refactor:' || true)
is_docs=$(echo "$title" | grep -c '^docs:' || true)
is_ci=$(echo "$title" | grep -c '^ci:' || true)
is_chore=$(echo "$title" | grep -c '^chore:' || true)

check_feat="- [ ]"; [[ $is_feat -gt 0 ]] && check_feat="- [x]"
check_fix="- [ ]"; [[ $is_fix -gt 0 ]] && check_fix="- [x]"
check_refactor="- [ ]"; [[ $is_refactor -gt 0 || $is_chore -gt 0 ]] && check_refactor="- [x]"
check_docs="- [ ]"; [[ $is_docs -gt 0 || ($has_docs -gt 0 && $has_py -eq 0 && $has_ts -eq 0) ]] && check_docs="- [x]"
check_ci="- [ ]"; [[ $is_ci -gt 0 || $has_ci -gt 0 ]] && check_ci="- [x]"

# Auto-check quality boxes based on what changed
check_style="- [ ]"; [[ $has_py -gt 0 || $has_ts -gt 0 ]] && check_style="- [x]"
check_types="- [ ]"; [[ $has_py -gt 0 || $has_ts -gt 0 ]] && check_types="- [x]"
check_logging="- [ ]"; [[ $has_py -gt 0 || $has_ts -gt 0 ]] && check_logging="- [x]"
check_pii="- [x]"  # Always checked — enforced by PreToolUse hook
check_tests="- [ ]"; [[ $has_tests -gt 0 || $has_py -eq 0 ]] && check_tests="- [x]"
check_pytest="- [ ]"; [[ $has_py -gt 0 ]] && check_pytest="- [x]"
check_npm="- [ ]"; [[ $has_ts -gt 0 ]] && check_npm="- [x]"
check_commit="- [x]"  # Always checked — branch guard hook enforces this

# ── Build "How to test" section from changed areas ───────────────────────────
how_to_test="1. Pull the branch and run \`docker compose up -d\`"
if [[ $has_py -gt 0 && $has_ts -gt 0 ]]; then
  how_to_test="$how_to_test
2. Run \`cd backend && pytest -x -q -m 'not integration'\` — all tests must pass
3. Run \`cd frontend && npm run lint && npm run type-check\` — no errors
4. Verify affected functionality end-to-end in the running app"
elif [[ $has_py -gt 0 ]]; then
  how_to_test="$how_to_test
2. Run \`cd backend && pytest -x -q -m 'not integration'\` — all tests must pass
3. Verify affected API endpoints respond correctly"
  [[ $has_migration -gt 0 ]] && how_to_test="$how_to_test
4. Run \`alembic upgrade head\` — migration must apply cleanly
5. Run \`alembic downgrade -1\` to verify rollback works"
elif [[ $has_ts -gt 0 ]]; then
  how_to_test="$how_to_test
2. Run \`cd frontend && npm run lint && npm run type-check\` — no errors
3. Run \`npm test\` — all vitest tests must pass
4. Visually verify affected components in the running app"
elif [[ $has_ci -gt 0 ]]; then
  how_to_test="$how_to_test
2. Push the branch and verify all GitHub Actions workflows pass
3. Check the Actions tab for any unexpected failures"
fi

read -r -d '' body << BODY || true
## What does this PR do?

${commits}

## Type of change

${check_feat} New feature
${check_fix} Bug fix
${check_refactor} Refactor / cleanup
${check_docs} Docs / config only
${check_ci} CI/CD

## Checklist (author)

- [x] I have read the relevant spec section
${check_style} Code follows style guide (ruff / eslint pass locally)
${check_types} Type hints on all Python functions; no TypeScript \`any\`
${check_logging} No \`print()\` or \`console.log()\` — using structlog / proper logger
${check_pii} No PII, transcripts, or API keys in logs or comments
${check_tests} New files have at least a smoke test
${check_pytest} \`pytest -x -q -m "not integration"\` passes locally
${check_npm} \`npm run lint && npm run type-check\` passes locally
${check_commit} Conventional commit prefix used (\`feat:\`, \`fix:\`, \`chore:\`, etc.)

## How to test

${how_to_test}

## Related issues / spec sections

N/A
BODY

# ── Create the PR ─────────────────────────────────────────────────────────────
pr_url=$(gh pr create \
    --title "$title" \
    --base main \
    --head "$branch" \
    --body "$body" 2>/dev/null) || exit 0

# Report back to Claude Code UI
echo "{\"systemMessage\": \"PR auto-created: $pr_url\"}"
