"""Unit tests for Dashboard API."""

from __future__ import annotations

import contextlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.models.interview_session import InterviewSession, SessionStatus, SessionType
from app.models.segment_score import SegmentScore
from app.models.skill_graph_node import SkillGraphNode, SkillTrend
from app.models.story import Story
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


def _make_session(user_id: uuid.UUID, score: int = 70) -> InterviewSession:
    s = MagicMock(spec=InterviewSession)
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.type = SessionType.BEHAVIORAL
    s.status = SessionStatus.COMPLETED
    s.total_cost_usd = Decimal("0.35")
    s.created_at = datetime.now(UTC)
    s.lint_results = {"average_score": score, "segments_scored": 2}
    return s


def _make_seg_score(session_id: uuid.UUID, score: int = 70) -> SegmentScore:
    s = MagicMock(spec=SegmentScore)
    s.id = uuid.uuid4()
    s.session_id = session_id
    s.overall_score = score
    return s


def _make_skill(user_id: uuid.UUID, name: str, score: int) -> SkillGraphNode:
    n = MagicMock(spec=SkillGraphNode)
    n.id = uuid.uuid4()
    n.user_id = user_id
    n.skill_name = name
    n.skill_category = "behavioral"
    n.current_score = score
    n.best_score = score + 5
    n.trend = SkillTrend.STABLE
    return n


def _make_story(user_id: uuid.UUID, competencies: list[str]) -> Story:
    s = MagicMock(spec=Story)
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.competencies = competencies
    s.times_used = 1
    s.best_score_with_this_story = 75
    return s


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.get = AsyncMock(return_value=None)
    return r


@pytest.fixture
def dash_client(mock_redis):
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


# ── GET /api/v1/dashboard ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_new_user(dash_client) -> None:
    """New user dashboard returns all zeros/nulls."""
    user = _make_user()
    db = AsyncMock()

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    async with dash_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 0
    assert data["total_skills_tracked"] == 0
    assert data["total_stories"] == 0
    assert data["avg_score_all_time"] is None
    assert data["readiness_estimate"] is None


@pytest.mark.asyncio
async def test_dashboard_active_user(dash_client) -> None:
    """User with sessions/skills/stories returns populated dashboard."""
    user = _make_user()

    session1 = _make_session(user.id, score=70)
    session2 = _make_session(user.id, score=80)
    seg1 = _make_seg_score(session1.id, 70)
    seg2 = _make_seg_score(session2.id, 80)
    skill1 = _make_skill(user.id, "star_structure", 55)
    skill2 = _make_skill(user.id, "tradeoff_analysis", 75)
    story1 = _make_story(user.id, ["technical_leadership"])

    db = AsyncMock()
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:  # all sessions
            result.scalars.return_value.all.return_value = [session1, session2]
        elif call_count == 2:  # segment scores
            result.scalars.return_value.all.return_value = [seg1, seg2]
        elif call_count == 3:  # skill nodes
            result.scalars.return_value.all.return_value = [skill1, skill2]
        elif call_count == 4:  # stories
            result.scalars.return_value.all.return_value = [story1]
        else:
            result.scalars.return_value.all.return_value = []
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    async with dash_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert data["total_sessions"] == 2
    assert data["sessions_scored"] == 2
    assert data["avg_score_all_time"] == 75.0
    assert data["best_session_score"] == 80
    assert data["total_skills_tracked"] == 2
    assert data["avg_skill_score"] == 65.0
    assert data["weakest_skill"] == "star_structure"
    assert data["strongest_skill"] == "tradeoff_analysis"
    assert data["total_stories"] == 1
    assert data["coverage_pct"] > 0
    assert data["readiness_estimate"] is not None
    assert len(data["recent_sessions"]) == 2


@pytest.mark.asyncio
async def test_dashboard_readiness_estimate_increases_with_sessions(dash_client) -> None:
    """Readiness estimate increases with more sessions."""
    user = _make_user()
    sessions = [_make_session(user.id, score=70) for _ in range(10)]
    skills = [_make_skill(user.id, f"skill_{i}", 70) for i in range(5)]

    db = AsyncMock()
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalars.return_value.all.return_value = sessions
        elif call_count == 2:
            result.scalars.return_value.all.return_value = [
                _make_seg_score(s.id, 70) for s in sessions
            ]
        elif call_count == 3:
            result.scalars.return_value.all.return_value = skills
        else:
            result.scalars.return_value.all.return_value = []
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    async with dash_client(db, user=user) as (client, _):
        response = await client.get("/api/v1/dashboard")

    data = response.json()
    assert data["readiness_estimate"] is not None
    assert data["readiness_estimate"] > 50  # 10 sessions + avg skill 70 should be reasonably high


@pytest.mark.asyncio
async def test_dashboard_unauthenticated(mock_redis) -> None:
    """Dashboard requires auth."""
    db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_redis] = lambda: mock_redis
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/dashboard")
        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()
