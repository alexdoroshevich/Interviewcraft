"""Unit tests for Negotiation API.

Tests: start session, list history, analysis retrieval, pattern detection.
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.negotiation import _HIDDEN_MAX_MULTIPLIER
from app.database import get_db
from app.main import app
from app.models.interview_session import InterviewSession, SessionStatus, SessionType
from app.models.user import User, UserRole
from app.redis_client import get_redis
from app.services.auth.dependencies import get_current_user

# ── Fixtures ───────────────────────────────────────────────────────────────────


def _make_user() -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.email = "test@example.com"
    u.role = UserRole.user
    u.is_active = True
    return u


def _make_neg_session(
    user_id: uuid.UUID,
    company: str = "Google",
    offer: int = 200000,
    score: int = 65,
) -> InterviewSession:
    s = MagicMock(spec=InterviewSession)
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.type = SessionType.NEGOTIATION
    s.status = SessionStatus.COMPLETED
    s.quality_profile = "balanced"
    s.total_cost_usd = 0
    s.created_at = datetime.now(UTC)
    s.ended_at = datetime.now(UTC)
    s.transcript = []
    s.lint_results = {
        "negotiation_context": {
            "company": company,
            "role": "Senior SWE",
            "level": "L5",
            "offer_amount": offer,
            "market_rate": 220000,
            "hidden_max": int(offer * _HIDDEN_MAX_MULTIPLIER),
            "lowball": int(offer * 0.9),
        },
        "negotiation_analysis": {
            "negotiation_scores": {
                "anchoring": 60,
                "value_articulation": 55,
                "counter_strategy": 50,
                "emotional_control": 70,
                "money_left_on_table": 15000,
            },
            "overall_score": score,
            "improvement_notes": ["Anchor higher next time."],
            "money_left_on_table": 15000,
        },
    }
    return s


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.get = AsyncMock(return_value=None)
    return r


@pytest.fixture
def neg_client(mock_redis):
    @contextlib.asynccontextmanager
    async def _build(db_mock, user=None):
        _user = user or _make_user()
        app.dependency_overrides[get_current_user] = lambda: _user
        app.dependency_overrides[get_db] = lambda: db_mock
        app.dependency_overrides[get_redis] = lambda: mock_redis
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                yield c, _user
        finally:
            app.dependency_overrides.clear()

    return _build


# ── Hidden max computation ─────────────────────────────────────────────────────


def test_hidden_max_multiplier_reasonable() -> None:
    """Hidden max should be 10-20% above offer."""
    assert 1.1 <= _HIDDEN_MAX_MULTIPLIER <= 1.25


# ── POST /api/v1/negotiation/start ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_negotiation_success(neg_client) -> None:
    """201 returned with session_id and context."""
    user = _make_user()

    created_session = MagicMock(spec=InterviewSession)
    created_session.id = uuid.uuid4()

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda s: None)

    def set_session(s: MagicMock) -> None:
        s.id = created_session.id

    db.refresh = AsyncMock(side_effect=set_session)

    async with neg_client(db, user=user) as (client, _):
        response = await client.post(
            "/api/v1/negotiation/start",
            json={
                "company": "Google",
                "role": "Senior SWE",
                "level": "L5",
                "offer_amount": 200000,
                "market_rate": 220000,
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["company"] == "Google"
    assert data["offer_amount"] == 200000
    assert "session_id" in data
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_start_negotiation_invalid_amount(neg_client) -> None:
    """422 when offer_amount is zero or negative."""
    user = _make_user()
    db = AsyncMock()

    async with neg_client(db, user=user) as (client, _):
        response = await client.post(
            "/api/v1/negotiation/start",
            json={
                "company": "Google",
                "role": "SWE",
                "level": "L5",
                "offer_amount": -1,
                "market_rate": 200000,
            },
        )

    assert response.status_code == 422


# ── GET /api/v1/negotiation/history ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_negotiation_history_empty(neg_client) -> None:
    """Empty list when no negotiation sessions."""
    user = _make_user()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    async with neg_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/negotiation/history")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_negotiation_history_with_sessions(neg_client) -> None:
    """History returned with score and money_left_on_table."""
    user = _make_user()
    session = _make_neg_session(user.id, company="Meta", offer=250000, score=72)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [session]
    db.execute = AsyncMock(return_value=mock_result)

    async with neg_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/negotiation/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["company"] == "Meta"
    assert data[0]["overall_score"] == 72
    assert data[0]["money_left_on_table"] == 15000


# ── GET /api/v1/negotiation/{id}/analysis ────────────────────────────────────


@pytest.mark.asyncio
async def test_negotiation_analysis_existing(neg_client) -> None:
    """Analysis returned from stored negotiation_analysis."""
    user = _make_user()
    session = _make_neg_session(user.id, score=68)

    db = AsyncMock()
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = session
        else:  # pattern detection — sessions list
            result.scalars.return_value.all.return_value = [session]
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    async with neg_client(db, user=user) as (client, _):
        response = await client.get(f"/api/v1/negotiation/{session.id}/analysis")

    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 68
    assert data["negotiation_scores"]["anchoring"] == 60
    assert data["hidden_max"] == int(200000 * _HIDDEN_MAX_MULTIPLIER)


@pytest.mark.asyncio
async def test_negotiation_analysis_not_found(neg_client) -> None:
    """404 when session doesn't exist or isn't negotiation type."""
    user = _make_user()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    async with neg_client(db, user=user) as (client, _):
        response = await client.get(f"/api/v1/negotiation/{uuid.uuid4()}/analysis")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_negotiation_unauthenticated(mock_redis) -> None:
    """Negotiation endpoints require auth."""
    db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/negotiation/history")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
