"""Unit tests for app.services.auth.dependencies — get_current_user and get_current_admin."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.models.user import User, UserRole
from app.services.auth.dependencies import get_current_admin, get_current_user
from app.services.auth.jwt_utils import create_access_token, create_refresh_token

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_user(*, is_active: bool = True, role: UserRole = UserRole.user) -> MagicMock:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.email = "test@example.com"
    u.is_active = is_active
    u.role = role
    return u


def _make_db(user: MagicMock | None) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = user
    db.execute = AsyncMock(return_value=result)
    return db


def _make_credentials(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


# ── No credentials ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_no_credentials_raises_401() -> None:
    """Missing credentials → 401."""
    db = _make_db(None)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=None, db=db)
    assert exc_info.value.status_code == 401


# ── Wrong token type ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_refresh_token_rejected() -> None:
    """Sending a refresh token (type='refresh') must be rejected → 401."""
    user_id = uuid.uuid4()
    refresh_token = create_refresh_token(user_id)
    creds = _make_credentials(refresh_token)
    db = _make_db(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds, db=db)
    assert exc_info.value.status_code == 401


# ── Valid token but user not found ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_user_not_found_raises_401() -> None:
    """Valid access token but user deleted from DB → 401."""
    user_id = uuid.uuid4()
    token = create_access_token(user_id, "user@example.com", "user")
    creds = _make_credentials(token)
    db = _make_db(None)  # user not found

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds, db=db)
    assert exc_info.value.status_code == 401


# ── Inactive user ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_inactive_user_raises_401() -> None:
    """Valid token but user is_active=False → 401."""
    inactive_user = _make_user(is_active=False)
    user_id = inactive_user.id
    token = create_access_token(user_id, "user@example.com", "user")
    creds = _make_credentials(token)
    db = _make_db(inactive_user)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds, db=db)
    assert exc_info.value.status_code == 401


# ── Invalid token string ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_garbage_token_raises_401() -> None:
    """Garbage token string → JWT decode error → 401."""
    creds = _make_credentials("not.a.valid.jwt.token")
    db = _make_db(None)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(credentials=creds, db=db)
    assert exc_info.value.status_code == 401


# ── Happy path ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_user_valid_credentials_returns_user() -> None:
    """Valid access token + active user → returns user object."""
    user = _make_user()
    token = create_access_token(user.id, user.email, "user")
    creds = _make_credentials(token)
    db = _make_db(user)

    result = await get_current_user(credentials=creds, db=db)
    assert result is user


# ── Admin dependency ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_current_admin_regular_user_raises_403() -> None:
    """Regular user role → 403 Forbidden."""
    user = _make_user(role=UserRole.user)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_admin(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_admin_admin_user_returns_user() -> None:
    """Admin role → returns admin user."""
    admin = _make_user(role=UserRole.admin)

    result = await get_current_admin(current_user=admin)
    assert result is admin
