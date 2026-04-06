"""HTTP tests for share card endpoints.

Covers:
- POST /api/v1/share/card (authenticated): 422 no skills, 201 success
- GET  /api/v1/share/card/{token} (public): 200 success, 404 not found, 404 expired
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
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
def authed_user() -> MagicMock:
    """Minimal authenticated user mock."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "test@example.com"
    return user


@pytest.fixture
async def authed_client(mock_redis: AsyncMock, mock_db: AsyncMock, authed_user: MagicMock):
    """Test client with auth + DB + Redis overridden."""
    app.dependency_overrides[get_current_user] = lambda: authed_user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def public_client(mock_redis: AsyncMock, mock_db: AsyncMock):
    """Test client with DB + Redis overridden but NO auth override (public endpoints)."""
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── POST /api/v1/share/card ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_share_card_no_skills_returns_422(
    authed_client: AsyncClient,
    mock_db: AsyncMock,
) -> None:
    """When the user has no skill nodes, card creation should return 422."""
    # First execute call: skills query → empty list
    skills_result = MagicMock()
    skills_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=skills_result)

    response = await authed_client.post("/api/v1/share/card")

    assert response.status_code == 422
    assert "scored session" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_share_card_success_returns_201(
    authed_client: AsyncClient,
    mock_db: AsyncMock,
) -> None:
    """Successful card creation returns 201 with token and share_url."""
    # Build mock skill nodes
    node1 = MagicMock()
    node1.skill_name = "star_structure"
    node1.skill_category = "behavioral"
    node1.current_score = 65

    node2 = MagicMock()
    node2.skill_name = "scalability_thinking"
    node2.skill_category = "system_design"
    node2.current_score = 55

    skills_result = MagicMock()
    skills_result.scalars.return_value.all.return_value = [node1, node2]

    # COUNT of completed sessions → scalar_one() returns 1
    sessions_result = MagicMock()
    sessions_result.scalar_one.return_value = 1

    mock_db.execute = AsyncMock(side_effect=[skills_result, sessions_result])

    # db.refresh populates token on the ShareCard
    def _set_card_fields(card: MagicMock) -> None:
        card.token = "abc123token"
        card.expires_at = datetime.now(UTC) + timedelta(days=30)

    mock_db.refresh = AsyncMock(side_effect=_set_card_fields)

    response = await authed_client.post("/api/v1/share/card")

    assert response.status_code == 201
    body = response.json()
    assert "token" in body
    assert "share_url" in body
    assert body["share_url"].startswith("/share/")


# ── GET /api/v1/share/card/{token} ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_share_card_success(
    public_client: AsyncClient,
    mock_db: AsyncMock,
) -> None:
    """GET with a valid, non-expired token returns 200 and snapshot data."""
    card = MagicMock()
    card.token = "abc123"
    card.snapshot_data = {
        "readiness_score": 72,
        "avg_skill_score": 68.5,
        "skill_scores_by_category": {"behavioral": 68.5},
        "top_strengths": ["Star Structure"],
        "session_count": 3,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    card.created_at = datetime.now(UTC)
    card.expires_at = datetime.now(UTC) + timedelta(days=30)  # future = valid

    result = MagicMock()
    result.scalar_one_or_none.return_value = card
    mock_db.execute = AsyncMock(return_value=result)

    response = await public_client.get("/api/v1/share/card/abc123")

    assert response.status_code == 200
    body = response.json()
    assert body["token"] == "abc123"
    assert "snapshot" in body
    assert body["snapshot"]["readiness_score"] == 72


@pytest.mark.asyncio
async def test_get_share_card_not_found(
    public_client: AsyncClient,
    mock_db: AsyncMock,
) -> None:
    """GET with an unknown token returns 404."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    response = await public_client.get("/api/v1/share/card/doesnotexist")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_share_card_expired(
    public_client: AsyncClient,
    mock_db: AsyncMock,
) -> None:
    """GET with an expired token returns 404."""
    card = MagicMock()
    card.token = "expiredtoken"
    card.snapshot_data = {
        "readiness_score": 50,
        "avg_skill_score": 50.0,
        "skill_scores_by_category": {},
        "top_strengths": [],
        "session_count": 1,
        "generated_at": datetime.now(UTC).isoformat(),
    }
    card.created_at = datetime.now(UTC) - timedelta(days=60)
    card.expires_at = datetime.now(UTC) - timedelta(days=1)  # past = expired

    result = MagicMock()
    result.scalar_one_or_none.return_value = card
    mock_db.execute = AsyncMock(return_value=result)

    response = await public_client.get("/api/v1/share/card/expiredtoken")

    assert response.status_code == 404
    assert "expired" in response.json()["detail"].lower()
