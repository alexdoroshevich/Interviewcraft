"""Session endpoint tests.

Unit tests mock the database — no live PostgreSQL required.
Integration tests (@pytest.mark.integration) require a live stack.

Coverage:
  POST   /api/v1/sessions      — create (normal + first-session forced to diagnostic)
  GET    /api/v1/sessions      — list (empty and non-empty)
  GET    /api/v1/sessions/{id} — detail with transcript
  PATCH  /api/v1/sessions/{id} — end (completed / abandoned / already-ended 409)
  Auth   — unauthenticated → 403, invalid type → 422
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.database import get_db
from app.main import app
from app.models.interview_session import InterviewSession, SessionStatus
from app.services.auth.dependencies import get_current_user

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_user() -> MagicMock:
    """Minimal mock User object."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "tester@example.com"
    user.is_active = True
    return user


def _make_session(
    user_id: uuid.UUID,
    type_: str = "behavioral",
    status: str = "active",
    transcript: list | None = None,
) -> MagicMock:
    """Minimal mock InterviewSession."""
    s = MagicMock(spec=InterviewSession)
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.type = type_
    s.interview_type = None
    s.status = status
    s.quality_profile = "balanced"
    s.total_cost_usd = Decimal("0.000")
    s.created_at = datetime.now(tz=UTC)
    s.ended_at = None
    s.transcript = transcript or []
    s.lint_results = None
    s.voice_id = None
    s.persona = "neutral"
    s.company = None
    s.focus_skill = None
    return s


def _mock_db(execute_side_effects: list | None = None) -> AsyncMock:
    """Return a mock AsyncSession with configurable execute() side effects."""
    db = AsyncMock()
    if execute_side_effects is not None:
        db.execute = AsyncMock(side_effect=execute_side_effects)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _scalar(value: object) -> MagicMock:
    """Wrap a value in a mock that supports .scalar_one_or_none()."""
    r = MagicMock()
    r.scalar_one_or_none.return_value = value
    return r


def _scalars_all(values: list) -> MagicMock:
    """Wrap a list in a mock that supports .scalars().all()."""
    r = MagicMock()
    r.scalars.return_value.all.return_value = values
    return r


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def authed_client(mock_redis):
    """
    Async test client where get_current_user is short-circuited to a real
    mock user, and get_db is replaced per-test via a closure.
    """
    # This fixture yields a factory so each test can inject its own db mock.
    import contextlib

    @contextlib.asynccontextmanager
    async def _build(db_mock: AsyncMock, user: MagicMock | None = None):
        _user = user or _make_user()
        app.dependency_overrides[get_current_user] = lambda: _user
        app.dependency_overrides[get_db] = lambda: db_mock
        from app.redis_client import get_redis

        app.dependency_overrides[get_redis] = lambda: mock_redis
        try:
            async with AsyncClient(
                transport=__import__("httpx").ASGITransport(app=app),
                base_url="http://test",
            ) as c:
                yield c, _user
        finally:
            app.dependency_overrides.clear()

    return _build


# ── POST /api/v1/sessions ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session_behavioral(authed_client, mock_redis) -> None:
    """Normal session creation returns 201 with the requested type."""
    user = _make_user()
    session = _make_session(user.id, type_="behavioral")

    # execute() called once: check for existing sessions → returns one (not first time)
    db = _mock_db(execute_side_effects=[_scalar(_make_session(user.id))])

    # After refresh, set the type so model_validate works
    async def _refresh(s):
        s.type = "behavioral"
        s.id = session.id
        s.status = "active"
        s.quality_profile = "balanced"
        s.total_cost_usd = Decimal("0.000")
        s.created_at = datetime.now(tz=UTC)
        s.ended_at = None
        s.interview_type = None

    db.refresh = AsyncMock(side_effect=_refresh)

    async with authed_client(db, user) as (client, _):
        response = await client.post(
            "/api/v1/sessions",
            json={"type": "behavioral", "quality_profile": "balanced"},
        )

    assert response.status_code == 201
    assert response.json()["type"] == "behavioral"
    assert response.json()["status"] == "active"


@pytest.mark.asyncio
async def test_create_session_first_session_forced_diagnostic(authed_client) -> None:
    """First-ever session is forced to 'diagnostic' regardless of requested type."""
    user = _make_user()
    session = _make_session(user.id, type_="diagnostic")

    # No prior sessions
    db = _mock_db(execute_side_effects=[_scalar(None)])

    async def _refresh(s):
        s.type = "diagnostic"
        s.id = session.id
        s.status = "active"
        s.quality_profile = "balanced"
        s.total_cost_usd = Decimal("0.000")
        s.created_at = datetime.now(tz=UTC)
        s.ended_at = None
        s.interview_type = None

    db.refresh = AsyncMock(side_effect=_refresh)

    async with authed_client(db, user) as (client, _):
        response = await client.post(
            "/api/v1/sessions",
            json={"type": "behavioral", "quality_profile": "balanced"},
        )

    assert response.status_code == 201
    assert response.json()["type"] == "diagnostic"


@pytest.mark.asyncio
async def test_create_session_unauthenticated(client, mock_redis) -> None:
    """No auth token → 403 (HTTPBearer returns 403 when credentials absent)."""
    response = await client.post(
        "/api/v1/sessions",
        json={"type": "behavioral"},
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_session_invalid_type(authed_client) -> None:
    """Unknown session type fails Pydantic validation → 422."""
    db = _mock_db()
    async with authed_client(db) as (client, _):
        response = await client.post(
            "/api/v1/sessions",
            json={"type": "unknown_type"},
        )
    assert response.status_code == 422


# ── GET /api/v1/sessions ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_empty(authed_client) -> None:
    """User with no sessions gets []."""
    db = _mock_db(execute_side_effects=[_scalars_all([])])
    async with authed_client(db) as (client, _):
        response = await client.get("/api/v1/sessions")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_sessions_returns_multiple(authed_client) -> None:
    """List returns one entry per session in the DB result."""
    user = _make_user()
    s1 = _make_session(user.id, type_="diagnostic")
    s2 = _make_session(user.id, type_="behavioral")
    db = _mock_db(execute_side_effects=[_scalars_all([s1, s2])])

    async with authed_client(db, user) as (client, _):
        response = await client.get("/api/v1/sessions")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    types = {d["type"] for d in data}
    assert types == {"diagnostic", "behavioral"}


# ── GET /api/v1/sessions/{id} ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_session_detail_includes_transcript(authed_client) -> None:
    """GET /{id} returns SessionDetail with the transcript field."""
    user = _make_user()
    turns = [{"role": "assistant", "content": "Tell me about yourself.", "ts_ms": 0}]
    session = _make_session(user.id, type_="diagnostic", transcript=turns)

    db = _mock_db(execute_side_effects=[_scalar(session)])

    async with authed_client(db, user) as (client, _):
        response = await client.get(f"/api/v1/sessions/{session.id}")

    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert len(data["transcript"]) == 1
    assert data["transcript"][0]["role"] == "assistant"


@pytest.mark.asyncio
async def test_get_session_not_found(authed_client) -> None:
    """GET /{id} for a session that doesn't exist → 404."""
    db = _mock_db(execute_side_effects=[_scalar(None)])
    async with authed_client(db) as (client, _):
        response = await client.get(f"/api/v1/sessions/{uuid.uuid4()}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ── PATCH /api/v1/sessions/{id} ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_end_session_completed(authed_client) -> None:
    """PATCH /{id} with status=completed transitions active → completed."""
    user = _make_user()
    session = _make_session(user.id)
    session.status = SessionStatus.ACTIVE

    db = _mock_db(execute_side_effects=[_scalar(session)])

    async with authed_client(db, user) as (client, _):
        response = await client.patch(
            f"/api/v1/sessions/{session.id}",
            json={"status": "completed"},
        )

    assert response.status_code == 200
    # status was mutated on the mock object by the endpoint
    assert session.status == "completed"


@pytest.mark.asyncio
async def test_end_session_abandoned(authed_client) -> None:
    """PATCH /{id} with status=abandoned is also valid."""
    user = _make_user()
    session = _make_session(user.id)
    session.status = SessionStatus.ACTIVE

    db = _mock_db(execute_side_effects=[_scalar(session)])

    async with authed_client(db, user) as (client, _):
        response = await client.patch(
            f"/api/v1/sessions/{session.id}",
            json={"status": "abandoned"},
        )

    assert response.status_code == 200
    assert session.status == "abandoned"


@pytest.mark.asyncio
async def test_end_session_already_ended_returns_409(authed_client) -> None:
    """Ending an already-completed session returns 409 Conflict."""
    user = _make_user()
    session = _make_session(user.id)
    session.status = SessionStatus.COMPLETED  # not ACTIVE

    db = _mock_db(execute_side_effects=[_scalar(session)])

    async with authed_client(db, user) as (client, _):
        response = await client.patch(
            f"/api/v1/sessions/{session.id}",
            json={"status": "completed"},
        )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_end_session_invalid_status(authed_client) -> None:
    """PATCH with an unknown status value → 422."""
    db = _mock_db()
    async with authed_client(db) as (client, _):
        response = await client.patch(
            f"/api/v1/sessions/{uuid.uuid4()}",
            json={"status": "deleted"},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_byok_required_returns_402(authed_client) -> None:
    """3rd+ session with no BYOK and no platform key → 402."""
    from unittest.mock import patch

    user = _make_user()
    user.byok_keys = None  # no BYOK keys

    # Return 2 existing sessions so session_count >= free_session_limit
    sessions = [_make_session(user.id), _make_session(user.id)]
    db = _mock_db(execute_side_effects=[_scalars_all(sessions)])

    with patch("app.api.v1.sessions.settings.anthropic_api_key", ""):
        async with authed_client(db, user) as (client, _):
            response = await client.post(
                "/api/v1/sessions",
                json={"type": "behavioral", "quality_profile": "balanced"},
            )

    assert response.status_code == 402
    assert "free sessions" in response.json()["detail"].lower()
