# Database Conventions

## Stack
- PostgreSQL 16 (via Docker)
- SQLAlchemy 2.x async ORM (`AsyncSession`)
- Alembic for migrations
- Models in `backend/app/models/`
- DB session factory in `backend/app/database.py`

## Migration Rules
- Migration files: `backend/alembic/versions/<NNN>_<description>.py`
- Numbering: sequential (001, 002, ...). Current: 010
- NEVER use `::jsonb` cast syntax with asyncpg — use `CAST(:param AS jsonb)`
- NEVER use `json.dumps()` inline in SQL — pass Python objects, let SQLAlchemy serialize
  EXCEPTION: seeded JSONB data in `op.execute()` bulk inserts needs `json.dumps()` explicitly
- Enum types: always `create_type=False, checkfirst=True` to avoid duplicate type errors
- Always test with `alembic upgrade head` before committing

## Key Tables (current schema)

| Table | Key columns | Notes |
|-------|------------|-------|
| `users` | `id UUID`, `email`, `hashed_password`, `role`, `profile JSONB`, `byok_keys JSONB`, `resume_text TEXT` | `profile` holds app_settings, resume parsed data, self-assessment |
| `sessions` | `id UUID`, `user_id FK`, `type`, `status`, `quality_profile`, `persona`, `company`, `focus_skill`, `voice_id`, `scoring_result JSONB`, `transcript JSONB` | `type` enum: behavioral/system_design/coding_discussion/negotiation/diagnostic |
| `session_segments` | `id UUID`, `session_id FK`, `question`, `answer`, `score`, `evidence JSONB`, `lint_results JSONB` | One row per Q&A exchange |
| `transcript_words` | `id UUID`, `session_id FK`, `word`, `start_ms`, `end_ms`, `speaker` | TTL 14 days. Word-level timestamps for delivery analysis |
| `skill_nodes` | `id UUID`, `user_id FK`, `skill_name`, `skill_category`, `current_score`, `trend` | Categories: behavioral/system_design/communication/coding_discussion/negotiation |
| `skill_history` | `id UUID`, `skill_node_id FK`, `score`, `recorded_at` | Append-only history |
| `questions` | `id UUID`, `text`, `type`, `difficulty`, `skills_tested JSONB`, `company`, `times_used` | Bank of interview questions |
| `stories` | `id UUID`, `user_id FK`, `title`, `summary`, `competencies JSONB`, `times_used`, `best_score_with_this_story` | STAR story bank |
| `usage_logs` | `id UUID`, `user_id FK`, `provider`, `operation`, `input_tokens`, `output_tokens`, `cost_usd DECIMAL`, `latency_ms`, `cached BOOL` | Every LLM/STT/TTS call |

## ORM Patterns

```python
# Fetch single record with ownership check
result = await db.execute(
    select(Session).where(Session.id == session_id, Session.user_id == user.id)
)
session = result.scalar_one_or_none()
if session is None:
    raise HTTPException(status_code=404, detail="Session not found")

# Fetch list
result = await db.execute(
    select(SkillNode).where(SkillNode.user_id == user.id).order_by(SkillNode.current_score)
)
nodes = result.scalars().all()

# Insert
obj = MyModel(user_id=user.id, ...)
db.add(obj)
await db.commit()
await db.refresh(obj)
```

## JSONB Update Pattern
SQLAlchemy doesn't detect in-place JSONB mutations. Always reassign:
```python
# WRONG — SQLAlchemy won't detect this change:
user.profile["key"] = value

# CORRECT — reassign the whole dict:
updated = dict(user.profile or {})
updated["key"] = value
user.profile = updated
await db.commit()
```

## Redis
- Client: `backend/app/redis_client.py`
- Used for: session state, rate limiting, cache
- Eviction policy: `allkeys-lru`
- Always set TTL on cache keys — add ±10% jitter to prevent thundering herd

## Connection String
- Dev: `postgresql+asyncpg://interviewcraft:interviewcraft@localhost:5432/interviewcraft`
- Loaded from `DATABASE_URL` env var in `backend/app/config.py`
