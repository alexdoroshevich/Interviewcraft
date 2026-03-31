"""Extended auth endpoint tests covering paths not exercised in test_auth.py.

Covers:
- Register: duplicate email → 409
- Login: happy path → 200 + access_token
- Refresh: valid body token → new access token
- Refresh: missing token → 401
- Refresh: invalid token → 401
- Forgot-password: unknown email → 200 generic message, no reset_token
- Forgot-password: existing active user with password → 200 + reset_token (APP_ENV=test)
- Forgot-password: OAuth-only user (no hashed_password) → 200 generic message
- Reset-password: valid token → 200 success message
- Reset-password: invalid token → 400
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.api.v1.auth import _create_reset_token
from app.models.user import User
from app.services.auth.jwt_utils import create_refresh_token
from app.services.auth.password import hash_password


@pytest.fixture(autouse=True)
def _bypass_rate_limit(mock_redis: AsyncMock) -> None:
    """Patch rate_limit.get_redis so tests never hit real Redis rate limiting."""
    with patch("app.middleware.rate_limit.get_redis", new=AsyncMock(return_value=mock_redis)):
        yield


def _make_active_user(*, password: str | None = "OldPass1!") -> MagicMock:
    """Build a MagicMock that satisfies the User duck-type expected by auth routes."""
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.email = "user@test.com"
    user.is_active = True
    user.hashed_password = hash_password(password) if password else None
    user.google_id = None
    user.role = MagicMock()
    user.role.value = "user"
    user.failed_login_attempts = 0
    user.locked_until = None
    user.is_locked = MagicMock(return_value=False)
    return user


# ── Register: duplicate email → 409 ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """Second registration with the same email must return 409 Conflict."""
    existing_user = _make_active_user()

    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_user
    mock_db.execute = AsyncMock(return_value=result)

    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "user@test.com", "password": "NewPass1!"},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


# ── Login: happy path ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_success_returns_access_token(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Correct credentials return 200 with an access_token."""
    password = "CorrectPass1!"
    user = _make_active_user(password=password)

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=result)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ── Refresh: valid body token → new access token ──────────────────────────────


@pytest.mark.asyncio
async def test_refresh_with_valid_body_token_returns_new_access_token(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """A valid refresh token sent in the request body yields a new access token."""
    user = _make_active_user()
    refresh_token = create_refresh_token(user.id)

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=result)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# ── Refresh: missing token → 401 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_with_no_token_returns_401(client: AsyncClient) -> None:
    """Sending neither a cookie nor a body token must return 401."""
    response = await client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"] or "expired" in response.json()["detail"].lower()


# ── Refresh: invalid token → 401 ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(client: AsyncClient) -> None:
    """A garbage string in refresh_token must return 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "totally.not.valid"},
    )
    assert response.status_code == 401


# ── Forgot-password: unknown email → 200 (generic, no reset_token) ───────────


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_returns_200_generic(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """Unknown email must still return 200 to prevent email enumeration."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=result)

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nobody@nowhere.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "reset_token" not in data


# ── Forgot-password: active user with password → 200 + reset_token ───────────


@pytest.mark.asyncio
async def test_forgot_password_active_user_returns_reset_token_in_test_env(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """In APP_ENV=test (the default during pytest), the reset_token is included in the body."""
    user = _make_active_user(password="Password1!")

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=result)

    # The route does `from app.config import settings as _settings` inline,
    # so we patch the canonical settings object that that import resolves to.
    with patch("app.config.settings.app_env", "test"):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": user.email},
        )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    # reset_token is returned in dev/test mode
    assert "reset_token" in data


# ── Forgot-password: OAuth-only user → 200 generic (no reset_token) ──────────


@pytest.mark.asyncio
async def test_forgot_password_oauth_only_user_returns_200_generic(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """OAuth-only user (no hashed_password) gets a generic 200 — no reset link."""
    user = _make_active_user(password=None)  # no password
    user.google_id = "google-sub-abc123"

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=result)

    response = await client.post(
        "/api/v1/auth/forgot-password",
        json={"email": user.email},
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    # reset_token should NOT be present for OAuth-only users
    assert "reset_token" not in data


# ── Reset-password: valid token → 200 success ────────────────────────────────


@pytest.mark.asyncio
async def test_reset_password_valid_token_returns_200(
    client: AsyncClient, mock_db: AsyncMock
) -> None:
    """A valid reset token and a strong new password yields a 200 success message."""
    user = _make_active_user(password="OldPass1!")
    reset_token = _create_reset_token(str(user.id))

    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    mock_db.execute = AsyncMock(return_value=result)

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": reset_token, "new_password": "NewPass1!"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "reset" in data["message"].lower() or "success" in data["message"].lower()


# ── Reset-password: invalid token → 400 ──────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_password_invalid_token_returns_400(client: AsyncClient) -> None:
    """A garbage or expired reset token must return 400."""
    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "garbage.token.here", "new_password": "NewPass1!"},
    )

    assert response.status_code == 400
    assert (
        "invalid" in response.json()["detail"].lower()
        or "expired" in response.json()["detail"].lower()
    )


# ── Reset-password: wrong token type (access token) → 400 ────────────────────


@pytest.mark.asyncio
async def test_reset_password_wrong_token_type_returns_400(client: AsyncClient) -> None:
    """An access token (type='access') must not be accepted as a reset token → 400."""
    from app.services.auth.jwt_utils import create_access_token  # noqa: PLC0415

    user = _make_active_user()
    access_token = create_access_token(user.id, user.email, "user")

    response = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": access_token, "new_password": "NewPass1!"},
    )

    assert response.status_code == 400


# ── Google OAuth: invalid token → 401 ────────────────────────────────────────


@pytest.mark.asyncio
async def test_google_oauth_invalid_token_returns_401(client: AsyncClient) -> None:
    """Google tokeninfo returns non-200 → 401 Unauthorized."""
    mock_response = MagicMock()
    mock_response.status_code = 400

    with patch("httpx.AsyncClient") as mock_cls:
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(return_value=mock_response)

        response = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "invalid.google.token"},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_google_oauth_new_user_created(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Valid Google token for a new user creates the account and returns a token."""
    mock_google_resp = MagicMock()
    mock_google_resp.status_code = 200
    mock_google_resp.json.return_value = {
        "email": "newuser@gmail.com",
        "sub": "google-sub-999",
    }

    # DB: user not found by google_id/email, then create
    not_found = MagicMock()
    not_found.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=not_found)

    new_user = _make_active_user()
    new_user.email = "newuser@gmail.com"
    new_user.google_id = "google-sub-999"

    def _refresh(u: object) -> None:
        u.id = new_user.id  # type: ignore[attr-defined]
        u.email = new_user.email  # type: ignore[attr-defined]
        u.role = new_user.role  # type: ignore[attr-defined]

    mock_db.refresh = AsyncMock(side_effect=_refresh)

    with patch("httpx.AsyncClient") as mock_cls:
        mock_ctx = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_ctx)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_ctx.get = AsyncMock(return_value=mock_google_resp)

        response = await client.post(
            "/api/v1/auth/google",
            json={"id_token": "valid.google.id_token"},
        )

    assert response.status_code == 200
    assert "access_token" in response.json()


# ── Refresh: access token sent to /refresh → 401 (wrong token type) ──────────


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401(client: AsyncClient) -> None:
    """Sending an access token to /refresh must return 401 (wrong type)."""
    user = _make_active_user()
    from app.services.auth.jwt_utils import create_access_token  # noqa: PLC0415

    access_token = create_access_token(user.id, user.email, "user")

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401


# ── Refresh: valid refresh token but user not in DB → 401 ────────────────────


@pytest.mark.asyncio
async def test_refresh_user_not_found_returns_401(client: AsyncClient, mock_db: AsyncMock) -> None:
    """Valid refresh token but the user was deleted → 401."""
    user = _make_active_user()
    refresh_token = create_refresh_token(user.id)

    result = MagicMock()
    result.scalar_one_or_none.return_value = None  # user not in DB
    mock_db.execute = AsyncMock(return_value=result)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401
