# /check — Full type-check + lint pass

Runs TypeScript strict type-check on the frontend and ruff/mypy on the backend.
Use this before committing or when you're unsure if changes are type-safe.

## Steps

1. Run frontend TypeScript check:
```bash
cd frontend && npx tsc --noEmit 2>&1
```

2. Run backend ruff lint:
```bash
cd backend && python -m ruff check app/ 2>&1
```

3. Report: list all errors found. If clean, confirm "✓ No type errors or lint warnings."

Do not fix errors unless the user explicitly asks — just report them.
