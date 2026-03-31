"""HTTP endpoint tests for GET/POST /api/v1/questions/*.

Covers all 5 endpoints in app/api/v1/questions.py:
- GET  /api/v1/questions/next      → 404 when empty, 200 when question exists
- GET  /api/v1/questions           → 200 empty list, 200 with filters
- POST /api/v1/questions/contribute → 201 valid, 422 invalid type, 422 invalid difficulty
- GET  /api/v1/questions/contribute → 200 returns user's submissions
- POST /api/v1/questions/{id}/upvote → 204 success, 404 not found, 409 duplicate
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.main import app
from app.redis_client import get_redis
from app.services.auth.dependencies import get_current_user

# ── Fixture helpers ───────────────────────────────────────────────────────────


def _make_user() -> MagicMock:
    """Create a minimal authenticated user mock."""
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = "tester@example.com"
    user.is_active = True
    return user


def _make_question() -> MagicMock:
    """Create a minimal Question mock with all fields required by QuestionResponse."""
    q = MagicMock()
    q.id = uuid.uuid4()
    q.text = "Tell me about a time you led a complex project."
    q.type = "behavioral"
    q.difficulty = "l5"
    q.company = None
    q.skills_tested = ["star_structure", "ownership_signal"]
    q.status = "approved"
    q.times_used = 0
    q.upvotes = 0
    q.submitted_by = None
    q.created_at = datetime.now(UTC)
    return q


@asynccontextmanager
async def _authed_client(
    mock_db: AsyncMock,
    mock_redis: AsyncMock,
    user: MagicMock,
) -> AsyncIterator[AsyncClient]:
    """Build an AsyncClient with auth + DB + Redis overrides applied."""
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_redis, None)


# ── GET /api/v1/questions/next ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_next_question_404_when_no_questions(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """When the DB has no questions, /next must return 404."""
    user = _make_user()

    # skill_graph returns no weak nodes, DB returns no candidates
    empty_result = MagicMock()
    empty_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=empty_result)

    from unittest.mock import patch

    async with _authed_client(mock_db, mock_redis, user) as client:
        with patch(
            "app.api.v1.questions.skill_graph_service.get_weakest_skills",
            return_value=[],
        ):
            resp = await client.get("/api/v1/questions/next")

    assert resp.status_code == 404
    assert "No questions" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_get_next_question_200_returns_question(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """When at least one approved question exists, /next returns 200 + QuestionResponse."""
    user = _make_user()
    q = _make_question()

    result = MagicMock()
    result.scalars.return_value.all.return_value = [q]
    mock_db.execute = AsyncMock(return_value=result)

    from unittest.mock import patch

    async with _authed_client(mock_db, mock_redis, user) as client:
        with patch(
            "app.api.v1.questions.skill_graph_service.get_weakest_skills",
            return_value=[],
        ):
            resp = await client.get("/api/v1/questions/next")

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(q.id)
    assert data["type"] == "behavioral"


# ── GET /api/v1/questions ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_questions_empty_returns_200(mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    """Empty question bank returns 200 with an empty list."""
    user = _make_user()

    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=result)

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.get("/api/v1/questions")

    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_questions_with_filters_returns_200(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Filters (type, difficulty, company) are accepted and list is returned."""
    user = _make_user()
    q = _make_question()
    q.type = "system_design"
    q.difficulty = "l6"
    q.company = "google"

    result = MagicMock()
    result.scalars.return_value.all.return_value = [q]
    mock_db.execute = AsyncMock(return_value=result)

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.get(
            "/api/v1/questions",
            params={"type": "system_design", "difficulty": "l6", "company": "google"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "system_design"


# ── POST /api/v1/questions/contribute ────────────────────────────────────────


@pytest.mark.asyncio
async def test_contribute_question_valid_returns_201(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Valid contribution returns 201 with a 'pending' status and message."""
    user = _make_user()
    contributed = _make_question()
    contributed.type = "behavioral"
    contributed.difficulty = "l5"
    contributed.status = "pending"

    # refresh() populates the object after insert
    mock_db.refresh = AsyncMock(side_effect=lambda obj: None)

    # Make the question accessible after db.refresh via the mock object
    # The route calls db.refresh(question) and then uses question.id
    def _after_refresh(q: MagicMock) -> None:
        q.id = contributed.id
        q.status = "pending"

    mock_db.refresh = AsyncMock(side_effect=_after_refresh)

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.post(
            "/api/v1/questions/contribute",
            json={
                "text": "Tell me about a conflict you resolved at work.",
                "type": "behavioral",
                "difficulty": "l5",
                "skills_tested": ["conflict_resolution"],
            },
        )

    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert "review" in data["message"].lower() or "thank" in data["message"].lower()


@pytest.mark.asyncio
async def test_contribute_question_invalid_type_returns_422(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """An unrecognised question type must return 422 Unprocessable Entity."""
    user = _make_user()

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.post(
            "/api/v1/questions/contribute",
            json={
                "text": "Describe your leadership style in detail.",
                "type": "leadership",  # invalid
                "difficulty": "l5",
            },
        )

    assert resp.status_code == 422
    assert "type" in resp.json()["detail"].lower() or "invalid" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_contribute_question_invalid_difficulty_returns_422(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """An unrecognised difficulty value must return 422 Unprocessable Entity."""
    user = _make_user()

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.post(
            "/api/v1/questions/contribute",
            json={
                "text": "Walk me through how you would design a cache.",
                "type": "system_design",
                "difficulty": "easy",  # invalid — must be l4/l5/l6
            },
        )

    assert resp.status_code == 422
    assert "difficulty" in resp.json()["detail"].lower() or "l4" in resp.json()["detail"]


# ── GET /api/v1/questions/contribute ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_my_contributions_returns_200(mock_db: AsyncMock, mock_redis: AsyncMock) -> None:
    """GET /contribute returns a list of the current user's submitted questions."""
    user = _make_user()
    q = _make_question()
    q.submitted_by = user.id
    q.status = "pending"

    result = MagicMock()
    result.scalars.return_value.all.return_value = [q]
    mock_db.execute = AsyncMock(return_value=result)

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.get("/api/v1/questions/contribute")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == str(q.id)


# ── POST /api/v1/questions/{id}/upvote ───────────────────────────────────────


@pytest.mark.asyncio
async def test_upvote_question_success_returns_204(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Upvoting an existing question for the first time returns 204 No Content."""
    user = _make_user()
    q = _make_question()
    q.upvotes = 0

    result = MagicMock()
    result.scalar_one_or_none.return_value = q
    mock_db.execute = AsyncMock(return_value=result)
    mock_db.commit = AsyncMock()

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.post(f"/api/v1/questions/{q.id}/upvote")

    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_upvote_question_not_found_returns_404(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Upvoting a non-existent question returns 404."""
    user = _make_user()

    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    random_id = uuid.uuid4()

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.post(f"/api/v1/questions/{random_id}/upvote")

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upvote_question_duplicate_returns_409(
    mock_db: AsyncMock, mock_redis: AsyncMock
) -> None:
    """Upvoting the same question twice raises 409 Conflict."""
    user = _make_user()
    q = _make_question()

    result = MagicMock()
    result.scalar_one_or_none.return_value = q
    mock_db.execute = AsyncMock(return_value=result)

    # Simulate the DB unique constraint violation on the second upvote
    mock_db.commit = AsyncMock(side_effect=IntegrityError(None, None, None))
    mock_db.rollback = AsyncMock()

    async with _authed_client(mock_db, mock_redis, user) as client:
        resp = await client.post(f"/api/v1/questions/{q.id}/upvote")

    assert resp.status_code == 409
    assert "already" in resp.json()["detail"].lower() or "upvoted" in resp.json()["detail"].lower()
