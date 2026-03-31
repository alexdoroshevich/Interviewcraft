"""Tests for GET /api/v1/portfolio/export."""

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.main import app
from app.models.user import User, UserRole
from app.services.auth.dependencies import get_current_user


def _make_user() -> User:
    u = User()
    u.id = uuid.uuid4()
    u.email = "test@example.com"
    u.role = UserRole.user
    u.is_active = True
    u.failed_login_attempts = 0
    u.locked_until = None
    return u


@pytest.fixture()
def client_empty(mock_empty_db):
    user = _make_user()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_empty_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def mock_empty_db():
    db = AsyncMock(spec=AsyncSession)

    class _EmptyScalars:
        def all(self):
            return []

    class _EmptyResult:
        def scalars(self):
            return _EmptyScalars()

    db.execute = AsyncMock(return_value=_EmptyResult())
    return db


@pytest.fixture()
def client_anon():
    app.dependency_overrides.clear()
    with TestClient(app) as c:
        yield c


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_portfolio_requires_auth(client_anon):
    res = client_anon.get("/api/v1/portfolio/export")
    assert res.status_code == 401


def test_portfolio_public_empty(client_empty):
    res = client_empty.get("/api/v1/portfolio/export?visibility=public")
    assert res.status_code == 200
    data = res.json()
    assert data["visibility"] == "public"
    assert data["skill_graph"] == []
    assert data["session_count"] == 0
    assert data["avg_score_all_time"] is None
    # public mode: no stories key
    assert "stories" not in data


def test_portfolio_private_empty(client_empty):
    res = client_empty.get("/api/v1/portfolio/export?visibility=private")
    assert res.status_code == 200
    data = res.json()
    assert data["visibility"] == "private"
    # private mode: stories included (empty list)
    assert "stories" in data
    assert data["stories"] == []
    assert "segment_scores" in data


def test_portfolio_default_is_public(client_empty):
    res = client_empty.get("/api/v1/portfolio/export")
    assert res.status_code == 200
    assert res.json()["visibility"] == "public"


def test_portfolio_invalid_visibility(client_empty):
    res = client_empty.get("/api/v1/portfolio/export?visibility=secret")
    assert res.status_code == 422


def test_portfolio_exported_at_present(client_empty):
    res = client_empty.get("/api/v1/portfolio/export")
    data = res.json()
    assert "exported_at" in data
    assert "T" in data["exported_at"]  # ISO datetime format
