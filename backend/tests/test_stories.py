"""Unit tests for Story Bank API.

Tests: list, create, update, delete, coverage map, overuse warnings.
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.stories import _compute_warnings
from app.database import get_db
from app.main import app
from app.models.story import COMPETENCIES, Story
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


def _make_story(user_id: uuid.UUID, competencies: list[str] | None = None) -> Story:
    s = MagicMock(spec=Story)
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.title = "Database Migration at Startup X"
    s.summary = "Led PostgreSQL to DynamoDB migration for 500M records"
    s.competencies = competencies or ["technical_leadership", "execution"]
    s.times_used = 1
    s.last_used = datetime.now(UTC)
    s.best_score_with_this_story = 78
    s.warnings = []
    s.source_session_id = None
    s.auto_detected = False
    s.created_at = datetime.now(UTC)
    s.updated_at = datetime.now(UTC)
    return s


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.get = AsyncMock(return_value=None)
    return r


@pytest.fixture
def stories_client(mock_redis):
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


# ── _compute_warnings tests ───────────────────────────────────────────────────


def test_compute_warnings_no_overuse() -> None:
    story = MagicMock(spec=Story)
    story.times_used = 2
    story.competencies = ["technical_leadership"]
    warnings = _compute_warnings(story)
    assert warnings == []


def test_compute_warnings_overused() -> None:
    story = MagicMock(spec=Story)
    story.times_used = 4
    story.competencies = ["technical_leadership", "execution"]
    warnings = _compute_warnings(story)
    assert len(warnings) == 1
    assert "OVERUSED" in warnings[0]
    assert "4x" in warnings[0]


def test_compute_warnings_exact_threshold() -> None:
    story = MagicMock(spec=Story)
    story.times_used = 3  # exactly at threshold
    story.competencies = ["mentoring"]
    warnings = _compute_warnings(story)
    assert len(warnings) == 1


# ── COMPETENCIES list ─────────────────────────────────────────────────────────


def test_competencies_list_not_empty() -> None:
    assert len(COMPETENCIES) >= 8


def test_competencies_no_duplicates() -> None:
    assert len(COMPETENCIES) == len(set(COMPETENCIES))


# ── GET /api/v1/stories ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_stories_empty(stories_client) -> None:
    """Empty list returned when user has no stories."""
    user = _make_user()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    async with stories_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/stories")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_stories_returns_data(stories_client) -> None:
    """Stories returned with correct fields."""
    user = _make_user()
    story = _make_story(user.id)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [story]
    db.execute = AsyncMock(return_value=mock_result)

    async with stories_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/stories")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Database Migration at Startup X"
    assert "technical_leadership" in data[0]["competencies"]


# ── POST /api/v1/stories ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_story_success(stories_client) -> None:
    """Story created successfully with 201."""
    user = _make_user()
    saved_story = _make_story(user.id)

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock(side_effect=lambda s: None)

    # After refresh, simulate the story fields being set
    def set_story(s: MagicMock) -> None:
        s.id = saved_story.id
        s.user_id = user.id
        s.title = "New Story"
        s.summary = "A summary"
        s.competencies = ["execution"]
        s.times_used = 0
        s.last_used = None
        s.best_score_with_this_story = None
        s.warnings = []
        s.source_session_id = None
        s.auto_detected = False
        s.created_at = datetime.now(UTC)
        s.updated_at = datetime.now(UTC)

    db.refresh = AsyncMock(side_effect=set_story)

    async with stories_client(db, user=user) as (client, _):
        response = await client.post(
            "/api/v1/stories",
            json={
                "title": "New Story",
                "summary": "A summary",
                "competencies": ["execution"],
            },
        )

    assert response.status_code == 201
    db.add.assert_called_once()
    db.commit.assert_called_once()


# ── GET /api/v1/stories/coverage ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_coverage_map_no_stories(stories_client) -> None:
    """All competencies are gaps when no stories exist."""
    user = _make_user()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    async with stories_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/stories/coverage")

    assert response.status_code == 200
    data = response.json()
    assert data["total_stories"] == 0
    assert data["covered"] == 0
    assert data["gaps"] == len(COMPETENCIES)
    assert data["coverage_pct"] == 0.0


@pytest.mark.asyncio
async def test_coverage_map_with_stories(stories_client) -> None:
    """Coverage map reflects stories correctly."""
    user = _make_user()
    story1 = _make_story(user.id, competencies=["technical_leadership", "execution"])
    story2 = _make_story(user.id, competencies=["mentoring"])

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [story1, story2]
    db.execute = AsyncMock(return_value=mock_result)

    async with stories_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/stories/coverage")

    assert response.status_code == 200
    data = response.json()
    assert data["total_stories"] == 2
    assert data["covered"] == 3  # technical_leadership, execution, mentoring
    assert data["coverage_pct"] > 0

    # Check specific competencies
    comp_map = {c["competency"]: c for c in data["competencies"]}
    assert comp_map["technical_leadership"]["status"] in ("strong", "weak")
    assert comp_map["conflict_resolution"]["status"] == "gap"


# ── DELETE /api/v1/stories/{id} ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_story_success(stories_client) -> None:
    """PUT /{id} updates title, summary, and competencies."""
    user = _make_user()
    story = _make_story(user.id)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = story
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    async with stories_client(db, user=user) as (client, _):
        response = await client.put(
            f"/api/v1/stories/{story.id}",
            json={
                "title": "Updated Title",
                "summary": "Updated summary",
                "competencies": ["technical_leadership"],
            },
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_story_not_found(stories_client) -> None:
    """PUT /{id} returns 404 when story does not belong to user."""
    user = _make_user()

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    async with stories_client(db, user=user) as (client, _):
        response = await client.put(
            f"/api/v1/stories/{uuid.uuid4()}",
            json={"title": "New Title"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_story_success(stories_client) -> None:
    """DELETE /{id} returns 204 when story exists."""
    user = _make_user()
    story = _make_story(user.id)

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = story
    db.execute = AsyncMock(return_value=mock_result)
    db.delete = AsyncMock()
    db.commit = AsyncMock()

    async with stories_client(db, user=user) as (client, _):
        response = await client.delete(f"/api/v1/stories/{story.id}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_story_not_found(stories_client) -> None:
    """404 when story doesn't exist."""
    user = _make_user()
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    async with stories_client(db, user=user) as (client, _):
        response = await client.delete(f"/api/v1/stories/{uuid.uuid4()}")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stories_unauthenticated(mock_redis) -> None:
    """Stories require auth."""
    db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/stories")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
