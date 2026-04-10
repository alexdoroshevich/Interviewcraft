This file contains the InterviewCraft codebase packed for LLM context.

Key architecture:
- Backend: FastAPI + SQLAlchemy 2.x async, Python 3.13, Alembic migrations
- Frontend: Next.js 15 App Router + TypeScript strict, Base UI components
- Voice pipeline: Deepgram STT → Claude LLM → ElevenLabs TTS (all streaming)
- DB: PostgreSQL 16, Redis for session state, asyncpg driver

Critical invariants:
- Every user-data query MUST filter by user_id
- JSONB mutations MUST reassign the whole dict (SQLAlchemy won't detect in-place changes)
- Use CAST(:x AS jsonb) never ::jsonb (asyncpg incompatibility)
- Audio never written to disk — WebSocket memory only
- structlog only, never print()
- Next Alembic migration: 019
