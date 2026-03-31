"""Tests for GET /api/v1/admin/metrics.

Covers:
- 403 for regular user
- 401 for unauthenticated
- 200 for admin with empty DB (zeros, no crash)
- KPI flags when no data
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth.dependencies import get_current_admin, get_current_user

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_user(role: UserRole = UserRole.user) -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = f"{role.value}@test.com"
    u.role = role
    u.is_active = True
    u.failed_login_attempts = 0
    u.locked_until = None
    return u


@pytest.fixture()
def client_user():
    """TestClient authenticated as a regular user."""
    user = _make_user(UserRole.user)
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def client_admin(mock_db):
    """TestClient authenticated as admin with mock DB."""
    admin = _make_user(UserRole.admin)
    app.dependency_overrides[get_current_user] = lambda: admin
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_db] = lambda: mock_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_db():
    """Async mock DB that returns empty results for all queries."""
    db = AsyncMock(spec=AsyncSession)

    class _EmptyResult:
        def one(self):
            return _EmptyRow()

        def __iter__(self):
            return iter([])

    class _EmptyRow:
        stt_p50 = None
        stt_p95 = None
        llm_p50 = None
        llm_p95 = None
        tts_p50 = None
        tts_p95 = None
        e2e_p50 = None
        e2e_p95 = None
        n = 0
        avg_score = None
        stddev = None
        total = 0
        rewound = 0
        completed = 0
        total_calls = 0
        total_cost = 0
        cached_calls = 0
        anthropic_cached = 0
        anthropic_total = 0

    db.execute = AsyncMock(return_value=_EmptyResult())
    return db


@pytest.fixture()
def client_anon():
    """TestClient with no auth."""
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_metrics_requires_auth(client_anon):
    res = client_anon.get("/api/v1/admin/metrics")
    assert res.status_code == 401


def test_metrics_requires_admin(client_user):
    # Regular user gets 403
    # We need to also override get_current_admin to use real dependency
    app.dependency_overrides.pop(get_current_admin, None)
    res = client_user.get("/api/v1/admin/metrics")
    assert res.status_code == 403


def test_metrics_empty_db_returns_zeros(client_admin):
    res = client_admin.get("/api/v1/admin/metrics")
    assert res.status_code == 200
    data = res.json()

    # Structure present
    assert "voice_7d" in data
    assert "scoring_30d" in data
    assert "usage_30d" in data
    assert "latency_trend" in data
    assert "kpi_latency_ok" in data

    # Empty DB → no latency data → kpi_latency_ok is False (no p95)
    assert data["kpi_latency_ok"] is False

    # Scores absent
    assert data["scoring_30d"]["avg_score"] is None
    assert data["scoring_30d"]["total_scored"] == 0

    # Usage zeros
    assert data["usage_30d"]["total_sessions"] == 0
    assert data["usage_30d"]["total_cost_usd"] == 0.0
    assert data["usage_30d"]["cache_hit_rate_pct"] == 0.0

    # No trend data
    assert data["latency_trend"] == []


def test_metrics_kpi_flags_all_false_when_empty(client_admin):
    res = client_admin.get("/api/v1/admin/metrics")
    data = res.json()
    # With no data: latency unknown → False, cache 0% → False, completion 0% → False
    assert data["kpi_latency_ok"] is False
    assert data["kpi_cache_ok"] is False
    assert data["kpi_completion_ok"] is False


def test_metrics_voice_structure(client_admin):
    res = client_admin.get("/api/v1/admin/metrics")
    v = res.json()["voice_7d"]
    assert "stt" in v and "llm_ttft" in v and "tts" in v and "e2e" in v
    for key in ("stt", "llm_ttft", "tts", "e2e"):
        assert "p50" in v[key] and "p95" in v[key]
    assert isinstance(v["sample_count"], int)
