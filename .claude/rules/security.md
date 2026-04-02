---
paths:
  - "backend/app/api/**"
  - "backend/app/services/byok.py"
  - "backend/app/services/auth/**"
  - "frontend/lib/api.ts"
---

# Security Rules

## Secrets
- Never commit `.env` files, API keys, or credentials
- Never hardcode secrets in source code — use environment variables
- BYOK keys are encrypted with Fernet (SHA-256 derived from SECRET_KEY)
- Never log API keys, even partially — use `mask_key()` for display

## Data Protection
- Never log PII: no emails, names, transcripts, or user answers in logs
- Audio never touches disk — WebSocket memory only
- Word-level timestamps have 14-day TTL in `transcript_words`
- Session transcripts stored in PostgreSQL JSONB — not in flat files

## Authentication
- JWT tokens with proper expiry
- bcrypt for password hashing (pinned `<4.0.0` for passlib compatibility)
- All API endpoints require authentication except `/health` and `/auth/*`
- CORS restricted to configured origins (ports 3000-3005 in dev)

## Input Validation
- All user input validated through Pydantic schemas
- Session types validated against enum
- Company names validated against allowed list
- File uploads: not supported by design (no file storage)

## OWASP Awareness
- SQL injection: mitigated by SQLAlchemy ORM (never raw SQL)
- XSS: mitigated by React's default escaping + Next.js CSP headers
- CSRF: mitigated by JWT Bearer tokens (not cookies)
- Bandit runs in CI for Python security scanning
- CodeQL runs on every PR + weekly for deep semantic analysis (Python + TypeScript)
- gitleaks runs in pre-commit for secret detection

## GitHub Actions Supply Chain Security
- **SHA pinning is the standard** — `@v4` tags are mutable and can be hijacked
  (March 2025: tj-actions/changed-files compromise affected 23,000+ repos via tag poisoning)
- All actions should be pinned to full 40-char commit SHA with a version comment:
  `uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683 # v4.2.2`
- Dependabot is configured to auto-PR action updates weekly — review before merging
- After any Dependabot action update: manually convert the new tag to SHA
- Never use `@master` or `@main` for third-party actions — unpinnable
- GitHub organization policy can now enforce SHA-only actions (Settings → Actions → Policy)
