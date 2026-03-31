"""Unit tests for the Rewind API.

Tests:
- start_rewind: 200 with valid segment, 404 on missing session, 404 on missing segment
- score_rewind: 200 with valid text, 422 on empty text, delta calculation
- _build_rewind_hint: hint content
- _build_delta_reason: reason string generation
"""

from __future__ import annotations

import contextlib
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.rewind import _build_delta_reason, _build_rewind_hint
from app.database import get_db
from app.main import app
from app.models.user import User, UserRole
from app.redis_client import get_redis
from app.schemas.skills import CategoryDelta
from app.services.auth.dependencies import get_current_user

# ── Fixtures ───────────────────────────────────────────────────────────────────


def _make_user(role: str = "user") -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.email = "test@example.com"
    u.role = UserRole.user if role == "user" else UserRole.admin
    u.is_active = True
    return u


def _make_session(user_id: uuid.UUID, session_id: uuid.UUID | None = None):
    s = MagicMock()
    s.id = session_id or uuid.uuid4()
    s.user_id = user_id
    s.status = "completed"
    s.type = "behavioral"
    s.quality_profile = "balanced"
    s.total_cost_usd = 0
    return s


def _make_segment(session_id: uuid.UUID, segment_id: uuid.UUID | None = None):
    seg = MagicMock()
    seg.id = segment_id or uuid.uuid4()
    seg.session_id = session_id
    seg.segment_index = 0
    seg.question_text = "Tell me about a challenge."
    seg.answer_text = "I once fixed a bug."
    seg.overall_score = 55
    seg.category_scores = {
        "structure": 50,
        "depth": 55,
        "communication": 60,
        "seniority_signal": 50,
    }
    seg.rules_triggered = [
        {"rule": "missing_metrics", "confidence": "strong", "fix": "Add numbers."}
    ]
    seg.rewind_count = 0
    seg.best_rewind_score = None
    return seg


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    r.get = AsyncMock(return_value=None)
    return r


@pytest.fixture
def authed_rewind_client(mock_redis):
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


# ── _build_rewind_hint tests ──────────────────────────────────────────────────


def test_build_rewind_hint_no_rules() -> None:
    hint = _build_rewind_hint([])
    assert "sharpen" in hint.lower() or "metrics" in hint.lower()


def test_build_rewind_hint_with_rules() -> None:
    rules = [
        {"rule": "missing_metrics", "confidence": "strong", "fix": "Add specific numbers."},
        {"rule": "no_star_structure", "confidence": "strong", "fix": "Use STAR format."},
    ]
    hint = _build_rewind_hint(rules)
    assert "This time:" in hint
    assert "Add specific numbers" in hint


# ── _build_delta_reason tests ─────────────────────────────────────────────────


def test_build_delta_reason_positive() -> None:
    reason = _build_delta_reason(
        delta=15,
        rules_fixed=["missing_metrics"],
        rules_new=[],
        cat_delta=CategoryDelta(structure=20, depth=5, communication=0, seniority_signal=0),
    )
    assert "15 points" in reason or "+15" in reason
    assert "missing metrics" in reason.lower() or "missing_metrics" in reason


def test_build_delta_reason_negative() -> None:
    reason = _build_delta_reason(
        delta=-8,
        rules_fixed=[],
        rules_new=["rambling"],
        cat_delta=CategoryDelta(structure=0, depth=0, communication=-10, seniority_signal=0),
    )
    assert "8 points" in reason or "-8" in reason
    assert "rambling" in reason


def test_build_delta_reason_zero() -> None:
    reason = _build_delta_reason(
        delta=0,
        rules_fixed=[],
        rules_new=[],
        cat_delta=CategoryDelta(),
    )
    assert "unchanged" in reason.lower()


# ── API tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_rewind_session_not_found(authed_rewind_client) -> None:
    """404 when session doesn't exist."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=mock_result)

    async with authed_rewind_client(db) as (client, user):
        response = await client.post(
            f"/api/v1/sessions/{uuid.uuid4()}/rewind",
            json={"segment_id": str(uuid.uuid4())},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_rewind_segment_not_found(authed_rewind_client) -> None:
    """404 when session exists but segment doesn't."""
    user = _make_user()
    session = _make_session(user.id)
    session_id = session.id

    db = AsyncMock()

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:  # session lookup
            result.scalar_one_or_none.return_value = session
        else:  # segment lookup
            result.scalar_one_or_none.return_value = None
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    async with authed_rewind_client(db, user=user) as (client, _):
        response = await client.post(
            f"/api/v1/sessions/{session_id}/rewind",
            json={"segment_id": str(uuid.uuid4())},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_start_rewind_success(authed_rewind_client) -> None:
    """200 with valid session and segment."""
    user = _make_user()
    session = _make_session(user.id)
    segment = _make_segment(session.id)

    db = AsyncMock()
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = session
        else:
            result.scalar_one_or_none.return_value = segment
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    async with authed_rewind_client(db, user=user) as (client, _):
        response = await client.post(
            f"/api/v1/sessions/{session.id}/rewind",
            json={"segment_id": str(segment.id)},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["segment_id"] == str(segment.id)
    assert data["question"] == "Tell me about a challenge."
    assert data["original_score"] == 55
    assert "hint" in data
    assert "rules_to_fix" in data


@pytest.mark.asyncio
async def test_score_rewind_empty_answer(authed_rewind_client) -> None:
    """422 when answer_text is empty."""
    user = _make_user()
    session = _make_session(user.id)
    segment = _make_segment(session.id)

    db = AsyncMock()
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        result = MagicMock()
        if call_count == 1:
            result.scalar_one_or_none.return_value = session
        else:
            result.scalar_one_or_none.return_value = segment
        return result

    db.execute = AsyncMock(side_effect=mock_execute)

    async with authed_rewind_client(db, user=user) as (client, _):
        response = await client.post(
            f"/api/v1/sessions/{session.id}/rewind/{segment.id}/score",
            json={"answer_text": "   "},
        )

    assert response.status_code == 422
