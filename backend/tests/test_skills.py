"""Unit tests for the Skills API.

Tests:
- GET /api/v1/skills — empty graph, graph with nodes
- GET /api/v1/skills/plan — empty plan, plan with slots
- GET /api/v1/skills/history — history response
- GET /api/v1/skills/best — best items
"""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.models.skill_graph_node import SkillGraphNode, SkillTrend
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


def _make_skill_node(
    user_id: uuid.UUID,
    skill_name: str = "star_structure",
    skill_category: str = "behavioral",
    score: int = 55,
    trend: str = SkillTrend.STABLE,
) -> SkillGraphNode:
    n = MagicMock(spec=SkillGraphNode)
    n.id = uuid.uuid4()
    n.user_id = user_id
    n.skill_name = skill_name
    n.skill_category = skill_category
    n.current_score = score
    n.best_score = score + 5
    n.trend = trend
    n.last_practiced = datetime.now(UTC)
    n.next_review_due = datetime.now(UTC)
    n.evidence_links = []
    n.typical_mistakes = []
    n.created_at = datetime.now(UTC)
    n.updated_at = datetime.now(UTC)
    return n


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.get = AsyncMock(return_value=None)
    return r


@pytest.fixture
def skills_client(mock_redis):
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


# ── GET /api/v1/skills ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_skills_empty(skills_client) -> None:
    """Empty skill graph returns zero counts."""
    user = _make_user()
    db = AsyncMock()

    with patch("app.api.v1.skills.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=[])

        async with skills_client(db, user=user) as (client, _):
            response = await client.get("/api/v1/skills")

    assert response.status_code == 200
    data = response.json()
    assert data["total_skills"] == 0
    assert data["nodes"] == []
    assert data["avg_score"] == 0.0


@pytest.mark.asyncio
async def test_get_skills_with_nodes(skills_client) -> None:
    """Graph with nodes returns correct averages and categories."""
    user = _make_user()
    db = AsyncMock()

    nodes = [
        _make_skill_node(user.id, "star_structure", "behavioral", 60),
        _make_skill_node(user.id, "tradeoff_analysis", "system_design", 40),
    ]

    with patch("app.api.v1.skills.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=nodes)

        async with skills_client(db, user=user) as (client, _):
            response = await client.get("/api/v1/skills")

    assert response.status_code == 200
    data = response.json()
    assert data["total_skills"] == 2
    assert len(data["nodes"]) == 2
    assert data["avg_score"] == 50.0
    # system_design avg = 40, behavioral avg = 60 → weakest = system_design
    assert data["weakest_category"] == "system_design"
    assert data["strongest_category"] == "behavioral"


# ── GET /api/v1/skills/plan ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_drill_plan_empty(skills_client) -> None:
    """Empty plan returns message."""
    user = _make_user()
    db = AsyncMock()

    empty_plan = {
        "slots": [],
        "total_skills": 0,
        "weakest_skill": None,
        "estimated_minutes_per_week": 0,
        "generated_at": datetime.now(UTC).isoformat(),
        "message": "No skill data yet.",
    }

    with patch("app.api.v1.skills.drill_planner") as mock_planner:
        mock_planner.generate_weekly_plan = AsyncMock(return_value=empty_plan)

        async with skills_client(db, user=user) as (client, _):
            response = await client.get("/api/v1/skills/plan")

    assert response.status_code == 200
    data = response.json()
    assert data["slots"] == []
    assert data["message"] == "No skill data yet."


@pytest.mark.asyncio
async def test_get_drill_plan_with_slots(skills_client) -> None:
    """Drill plan with slots is returned correctly."""
    user = _make_user()
    db = AsyncMock()

    plan_data = {
        "slots": [
            {
                "day": "Monday",
                "skill_name": "star_structure",
                "skill_category": "behavioral",
                "current_score": 35,
                "trend": "declining",
                "questions": 2,
                "estimated_minutes": 14,
                "focus_note": "Foundation needed.",
            }
        ],
        "total_skills": 5,
        "weakest_skill": "star_structure",
        "estimated_minutes_per_week": 14,
        "generated_at": datetime.now(UTC).isoformat(),
        "message": None,
    }

    with patch("app.api.v1.skills.drill_planner") as mock_planner:
        mock_planner.generate_weekly_plan = AsyncMock(return_value=plan_data)

        async with skills_client(db, user=user) as (client, _):
            response = await client.get("/api/v1/skills/plan")

    assert response.status_code == 200
    data = response.json()
    assert len(data["slots"]) == 1
    assert data["slots"][0]["day"] == "Monday"
    assert data["weakest_skill"] == "star_structure"


# ── GET /api/v1/skills/history ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_skill_history(skills_client) -> None:
    """History returns evidence links as history points."""
    user = _make_user()
    db = AsyncMock()

    node = _make_skill_node(user.id, "star_structure", "behavioral", 60)
    node.evidence_links = [
        {"date": "2026-02-01", "score": 45, "session_id": str(uuid.uuid4())},
        {"date": "2026-02-08", "score": 60, "session_id": str(uuid.uuid4())},
    ]

    with patch("app.api.v1.skills.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=[node])

        async with skills_client(db, user=user) as (client, _):
            response = await client.get("/api/v1/skills/history")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["skill_name"] == "star_structure"
    assert len(data[0]["history"]) == 2
    assert data[0]["history"][0]["score"] == 45


# ── GET /api/v1/skills/best ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_beat_your_best(skills_client) -> None:
    """Best scores returned ordered by gap."""
    user = _make_user()
    db = AsyncMock()

    best_data = [
        {
            "skill_name": "star_structure",
            "skill_category": "behavioral",
            "current_score": 50,
            "best_score": 75,
            "gap": 25,
            "can_beat": True,
        },
        {
            "skill_name": "tradeoff_analysis",
            "skill_category": "system_design",
            "current_score": 65,
            "best_score": 70,
            "gap": 5,
            "can_beat": True,
        },
    ]

    with patch("app.api.v1.skills.drill_planner") as mock_planner:
        mock_planner.get_best_scores = AsyncMock(return_value=best_data)

        async with skills_client(db, user=user) as (client, _):
            response = await client.get("/api/v1/skills/best")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["skill_name"] == "star_structure"
    assert data[0]["gap"] == 25


@pytest.mark.asyncio
async def test_skills_unauthenticated(mock_redis) -> None:
    """Skills endpoints require authentication."""
    db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/skills")

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
