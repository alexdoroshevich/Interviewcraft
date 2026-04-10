# /deploy — Deploy to staging or production

Deploys backend to Fly.io and frontend to Vercel.
Pass "staging" or "prod" as argument: `/deploy staging` or `/deploy prod`

## Steps

1. Run TypeScript check: `cd frontend && npx tsc --noEmit`
2. Run backend tests: `cd backend && python -m pytest -x -q`
3. If either fails — stop and report errors. Do NOT deploy broken code.
4. If both pass:

**For staging:**
```bash
fly deploy --config fly.staging.toml --strategy bluegreen 2>&1
```

**For prod:**
```bash
fly deploy --config fly.dev.toml --strategy bluegreen 2>&1
```

**Frontend (Vercel auto-deploys from git push — remind user):**
"Frontend deploys automatically when you push to main. Run `git push origin main` to trigger it."

5. After deploy: hit the health endpoint to confirm it's live:
```bash
curl -s https://<app>.fly.dev/health | jq .
```

Report the deployment URL and any errors.
