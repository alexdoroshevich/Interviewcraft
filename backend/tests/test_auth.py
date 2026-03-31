"""Auth endpoint tests.

Unit tests mock the database and Redis via dependency_overrides in conftest.py.
Integration tests (marked @pytest.mark.integration) require a live PostgreSQL + Redis.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.services.auth.jwt_utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from app.services.auth.password import hash_password, verify_password

# ── Password hashing ────────────────────────────────────────────────────────────


def test_hash_password_returns_string():
    hashed = hash_password("SecurePass1!")
    assert isinstance(hashed, str)
    assert hashed != "SecurePass1!"


def test_verify_password_correct():
    hashed = hash_password("SecurePass1!")
    assert verify_password("SecurePass1!", hashed) is True


def test_verify_password_wrong():
    hashed = hash_password("SecurePass1!")
    assert verify_password("WrongPassword", hashed) is False


# ── JWT utils ───────────────────────────────────────────────────────────────────


def test_access_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "test@example.com", "user")
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "test@example.com"
    assert payload["role"] == "user"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    user_id = uuid.uuid4()
    token = create_refresh_token(user_id)
    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["type"] == "refresh"
    assert "jti" in payload


def test_tokens_are_distinct():
    user_id = uuid.uuid4()
    access = create_access_token(user_id, "test@example.com", "user")
    refresh = create_refresh_token(user_id)
    assert access != refresh


# ── Registration endpoint (unit — DB mocked via conftest) ──────────────────────


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Register with valid credentials returns 201 + access token."""
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "newuser@example.com"
    mock_user.role = MagicMock()
    mock_user.role.value = "user"

    # execute() → email uniqueness check returns None (email not taken)
    not_taken = MagicMock()
    not_taken.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=not_taken)

    # refresh() simulates DB populating defaults (id, role)
    from app.models.user import UserRole

    def _refresh(u):
        u.id = mock_user.id
        if u.role is None:
            u.role = UserRole.user

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "newuser@example.com", "password": "SecurePass1!"},
    )

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient) -> None:
    """Password without uppercase should return 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "nouppercase1!"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient) -> None:
    """Password shorter than 8 chars should return 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "Short1"},
    )
    assert response.status_code == 422


# ── Login endpoint (unit) ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Wrong password returns 401 without revealing whether email exists."""
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.email = "user@example.com"
    mock_user.hashed_password = hash_password("RealPassword1!")
    mock_user.is_locked.return_value = False
    mock_user.failed_login_attempts = 0

    found = MagicMock()
    found.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=found)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "WrongPass999!"},
    )

    assert response.status_code == 401
    assert "Incorrect" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_locked_account_returns_429(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Locked account returns 429 with time remaining."""
    mock_user = MagicMock()
    mock_user.email = "locked@example.com"
    mock_user.locked_until = datetime.now(tz=UTC) + timedelta(minutes=10)
    mock_user.is_locked.return_value = True

    found = MagicMock()
    found.scalar_one_or_none.return_value = mock_user
    mock_db.execute = AsyncMock(return_value=found)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "locked@example.com", "password": "AnyPass1!"},
    )

    assert response.status_code == 429
    assert "locked" in response.json()["detail"].lower()


# ── Rate limiting ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rate_limit_exceeded(client: AsyncClient, mock_redis: AsyncMock) -> None:
    """6th request in the window returns 429.

    The rate limit middleware calls get_redis() directly (not via DI), so we
    patch it at the module level to inject the mock.
    """
    from unittest.mock import patch

    mock_redis.incr = AsyncMock(return_value=6)  # over the limit of 5

    with patch("app.middleware.rate_limit.get_redis", return_value=mock_redis):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "user@example.com", "password": "Pass1!"},
        )

    assert response.status_code == 429
    assert "Retry-After" in response.headers


# ── /me endpoint ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient) -> None:
    """No token → 403 (HTTPBearer returns 403 when no credentials)."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient) -> None:
    """Garbage token → 401."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.real.token"},
    )
    assert response.status_code == 401


# ── Health (smoke) ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
