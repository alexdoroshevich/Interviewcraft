"""Tests for digest endpoints and email service.

Tests:
  - build_digest_html produces valid HTML
  - send_email is a no-op when SMTP not configured
  - GET /api/v1/digest/preview returns HTML
  - POST /api/v1/digest/send returns 202
  - POST /api/v1/digest/send-all returns 403 for non-admin
  - POST /api/v1/digest/send-all returns 202 for admin
  - PATCH /api/v1/settings with email_digest=true persists the value
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.database import get_db
from app.main import app
from app.models.user import User, UserRole
from app.redis_client import get_redis
from app.services.auth.dependencies import get_current_user
from app.services.email import DigestStats, build_digest_html, send_email

# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_user(role: UserRole = UserRole.user, profile: dict | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.email = "digest@example.com"
    u.role = role
    u.is_active = True
    u.byok_keys = None
    u.profile = profile
    return u


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.incr = AsyncMock(return_value=1)
    r.expire = AsyncMock()
    return r


@pytest.fixture
def mock_db():
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    # Default: execute returns empty results
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=result_mock)
    return session


@pytest.fixture
def user():
    return _make_user()


@pytest.fixture
def admin_user():
    return _make_user(role=UserRole.admin)


@pytest.fixture
async def client(mock_redis, mock_db, user):
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client(mock_redis, mock_db, admin_user):
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: admin_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── Email service unit tests ──────────────────────────────────────────────────


def _sample_stats() -> DigestStats:
    return DigestStats(
        user_email="test@example.com",
        sessions_this_week=3,
        sessions_total=12,
        avg_score_this_week=67.5,
        avg_score_all_time=72.0,
        top_weaknesses=[("star_structure", 45), ("tradeoff_analysis", 50)],
        due_for_review=["conciseness", "edge_cases"],
        sessions_completed_total=12,
    )


def test_build_digest_html_contains_key_content() -> None:
    """HTML output should include user stats and skill names."""
    stats = _sample_stats()
    html = build_digest_html(stats)

    assert "InterviewCraft" in html
    assert "3" in html  # sessions_this_week
    assert "12" in html  # sessions_total
    assert "68" in html  # avg_score_this_week rounded
    assert "STAR Structure" in html
    assert "Tradeoff Analysis" in html
    assert "Conciseness" in html
    assert "sessions/new" in html  # CTA link present


def test_build_digest_html_no_data() -> None:
    """HTML should render gracefully when there's no skill data."""
    stats = DigestStats(
        user_email="empty@example.com",
        sessions_this_week=0,
        sessions_total=0,
        avg_score_this_week=None,
        avg_score_all_time=None,
        top_weaknesses=[],
        due_for_review=[],
        sessions_completed_total=0,
    )
    html = build_digest_html(stats)
    assert "No skill data yet" in html
    assert "Nothing due" in html


@pytest.mark.asyncio
async def test_send_email_no_op_when_smtp_not_configured() -> None:
    """send_email returns False silently when SMTP_HOST is empty."""
    config = Settings(smtp_host="")
    result = await send_email(
        to_email="x@example.com",
        subject="Test",
        html_body="<p>hi</p>",
        config=config,
    )
    assert result is False


# ── Endpoint tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_preview_digest_returns_html(client: AsyncClient) -> None:
    """GET /digest/preview returns 200 with HTML content."""
    resp = await client.get("/api/v1/digest/preview")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "InterviewCraft" in resp.text


@pytest.mark.asyncio
async def test_send_digest_to_self_returns_202(client: AsyncClient) -> None:
    """POST /digest/send returns 202 regardless of SMTP config."""
    resp = await client.post("/api/v1/digest/send")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] in ("queued", "skipped")


@pytest.mark.asyncio
async def test_send_all_digests_forbidden_for_user(client: AsyncClient) -> None:
    """POST /digest/send-all returns 403 for non-admin users."""
    resp = await client.post("/api/v1/digest/send-all")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_send_all_digests_allowed_for_admin(admin_client: AsyncClient) -> None:
    """POST /digest/send-all returns 202 for admin users."""
    with patch("app.api.v1.digest._send_all_digests", new=AsyncMock()):
        resp = await admin_client.post("/api/v1/digest/send-all")
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "enqueued"


# ── Settings integration ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_settings_email_digest(mock_redis, mock_db) -> None:
    """PATCH /settings with email_digest=true persists and is returned."""
    user = _make_user(profile={"app_settings": {}})

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.patch("/api/v1/settings", json={"email_digest": True})

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["email_digest"] is True


@pytest.mark.asyncio
async def test_get_settings_returns_email_digest_false_by_default(mock_redis, mock_db) -> None:
    """GET /settings returns email_digest=false when not set."""
    user = _make_user(profile=None)

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/settings")

    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["email_digest"] is False
