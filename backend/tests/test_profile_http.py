"""HTTP tests for profile / self-assessment endpoints.

Covers:
- PUT  /api/v1/profile/self-assessment: 200 valid, 422 invalid weak area
- GET  /api/v1/profile/self-assessment: not completed, completed
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.redis_client import get_redis
from app.services.auth.dependencies import get_current_user

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Minimal Redis mock."""
    mock = AsyncMock()
    mock.incr = AsyncMock(return_value=1)
    mock.expire = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_db() -> AsyncMock:
    """Minimal DB session mock."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_user() -> MagicMock:
    """Authenticated user with an empty profile."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    user.profile = {}
    return user


@pytest.fixture
async def authed_client(
    mock_redis: AsyncMock,
    mock_db: AsyncMock,
    mock_user: MagicMock,
):
    """Test client with auth + DB + Redis overridden."""
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── POST /api/v1/profile/self-assessment ──────────────────────────────────────


@pytest.mark.asyncio
async def test_save_self_assessment_valid_returns_200(
    authed_client: AsyncClient,
    mock_db: AsyncMock,
) -> None:
    """Valid self-assessment body is saved and returns 200 with the data."""
    payload = {
        "target_company": "google",
        "target_level": "L5",
        "weak_areas": ["star_structure", "data_structures"],
        "interview_timeline": "1_month",
    }

    response = await authed_client.post("/api/v1/profile/self-assessment", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["target_company"] == "google"
    assert body["target_level"] == "L5"
    assert "star_structure" in body["weak_areas"]
    assert "completed_at" in body
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_save_self_assessment_invalid_weak_area_returns_422(
    authed_client: AsyncClient,
) -> None:
    """A weak area not in the allow-list causes a 422 response."""
    payload = {
        "target_company": "acme",
        "target_level": "L4",
        "weak_areas": ["fake_skill"],
        "interview_timeline": "2_weeks",
    }

    response = await authed_client.post("/api/v1/profile/self-assessment", json=payload)

    assert response.status_code == 422
    assert "fake_skill" in response.json()["detail"]


# ── GET /api/v1/profile/self-assessment ───────────────────────────────────────


@pytest.mark.asyncio
async def test_get_self_assessment_not_completed_returns_false(
    mock_redis: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """User with empty profile returns completed=false."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "no-profile@example.com"
    user.profile = {}

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/api/v1/profile/self-assessment")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["completed"] is False
    assert body["data"] is None


@pytest.mark.asyncio
async def test_get_self_assessment_completed_returns_data(
    mock_redis: AsyncMock,
    mock_db: AsyncMock,
) -> None:
    """User with self_assessment in profile returns completed=true and the data."""
    completed_at = datetime.now(UTC).isoformat()
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "completed@example.com"
    user.profile = {
        "self_assessment": {
            "target_company": "meta",
            "target_level": "L6",
            "weak_areas": ["ownership", "leadership"],
            "interview_timeline": "this_week",
            "completed_at": completed_at,
        }
    }

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/api/v1/profile/self-assessment")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["completed"] is True
    assert body["data"]["target_company"] == "meta"
    assert body["data"]["target_level"] == "L6"
    assert "ownership" in body["data"]["weak_areas"]
