# API Conventions

## URL Structure
- All endpoints: `/api/v1/<resource>`
- Versioning is part of the path, not headers
- Plural nouns for collections: `/api/v1/sessions`, `/api/v1/skills`
- Sub-resources: `/api/v1/sessions/{id}/transcript`, `/api/v1/sessions/{id}/score`

## Authentication
- JWT Bearer token in `Authorization: Bearer <token>` header
- Get current user via `CurrentUser` dependency: `user: CurrentUser`
- `CurrentUser` is imported from `app.services.auth.dependencies`
- Public endpoints (no auth): `/health`, `/api/v1/auth/login`, `/api/v1/auth/register`, `/api/v1/auth/refresh`
- WebSocket auth: token passed as `?token=` query param

## Request / Response Schemas
- All request/response types defined in `backend/app/schemas/`
- Schemas use `pydantic` with `BaseModel`
- Response models always returned via `response_model=` on the route decorator
- Never return raw dicts — always use a typed schema
- IDs are always `UUID` (not int), serialized as strings in JSON

## Error Handling
- Use `HTTPException(status_code=..., detail="human message")` for API errors
- Standard status codes:
  - 400 Bad Request — invalid input
  - 401 Unauthorized — missing/invalid token
  - 403 Forbidden — authenticated but not allowed
  - 404 Not Found — resource doesn't exist OR belongs to another user (never leak existence)
  - 422 Unprocessable — file parse failure, validation logic error
  - 503 Service Unavailable — external API (Claude, Deepgram, ElevenLabs) down

## User Data Isolation
- EVERY query that fetches user data MUST filter by `user_id = current_user.id`
- ID-based routes must verify ownership: load resource, then check `resource.user_id == user.id`
- If not owner: raise `HTTPException(status_code=404)` (not 403 — don't leak existence)
- Never use `.get(id)` alone — always `.get(id)` then ownership check, or query with both filters

## Router Setup
Each router file follows this pattern:
```python
router = APIRouter(prefix="/api/v1/<resource>", tags=["<resource>"])
# Registered in backend/app/main.py via app.include_router(router)
```

## Async Pattern
- All route handlers are `async def`
- DB session via `db: Annotated[AsyncSession, Depends(get_db)]`
- Use `await db.execute(select(...))` + `.scalars().all()` or `.scalar_one_or_none()`
- Always `await db.commit()` after writes, `await db.refresh(obj)` to reload
- Always `await db.rollback()` in except blocks that modify state

## Cost Logging
Every LLM call must log to `usage_logs`:
```python
usage_log = UsageLog(
    user_id=user.id,
    provider="anthropic",
    operation="<operation_name>",
    input_tokens=..., output_tokens=...,
    cost_usd=Decimal(...),
    latency_ms=...,
    cached=False,
)
db.add(usage_log)
```

## WebSocket Sessions
- Path: `ws://<host>/api/v1/sessions/{id}/ws?token=<jwt>`
- Auth validated at connection time via `verify_token(token)`
- Session pipeline created per-connection, torn down on disconnect
- All audio processing in-memory — never write audio to disk
