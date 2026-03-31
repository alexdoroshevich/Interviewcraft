"""Unit tests for Settings and BYOK endpoints.

Tests: GET settings, PATCH quality profile, POST byok keys, DELETE byok keys.
Also tests the byok encryption/decryption service directly.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app
from app.models.user import User, UserRole
from app.redis_client import get_redis
from app.services.auth.dependencies import get_current_user
from app.services.byok import decrypt_api_key, decrypt_byok_keys, encrypt_api_key, mask_key

# ── Helpers ────────────────────────────────────────────────────────────────────

_SECRET = "test-secret-key-32chars-minimum!!"


def _make_user(byok_keys: dict | None = None, profile: dict | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = uuid.uuid4()
    u.email = "settings@example.com"
    u.role = UserRole.user
    u.is_active = True
    u.byok_keys = byok_keys
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
    return session


@pytest.fixture
def user():
    return _make_user()


@pytest.fixture
async def auth_client(mock_redis, mock_db, user):
    """Test client with auth stubbed to return our test user."""
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# ── BYOK service unit tests ───────────────────────────────────────────────────


def test_encrypt_decrypt_roundtrip():
    """Encrypt then decrypt should return original key."""
    raw = "sk-ant-api03-test-key-abcdef"
    encrypted = encrypt_api_key(raw, _SECRET)
    assert encrypted != raw
    assert decrypt_api_key(encrypted, _SECRET) == raw


def test_decrypt_wrong_secret_returns_none():
    """Decrypting with wrong secret should return None, not raise."""
    encrypted = encrypt_api_key("sk-ant-test", _SECRET)
    result = decrypt_api_key(encrypted, "wrong-secret-key-32chars-padding!")
    assert result is None


def test_mask_key():
    key = "sk-ant-api03-abcdef123456789xyz"
    masked = mask_key(key)
    assert "sk-ant-" in masked
    assert "xyz" in masked
    assert key not in masked


def test_mask_key_short():
    assert mask_key("abc") == "****"


def test_decrypt_byok_keys_empty():
    result = decrypt_byok_keys(None, _SECRET)
    assert result == {}


def test_decrypt_byok_keys_mixed():
    enc_anthropic = encrypt_api_key("sk-ant-real", _SECRET)
    byok = {"anthropic": enc_anthropic, "unknown_provider": "ignored"}
    result = decrypt_byok_keys(byok, _SECRET)
    assert result == {"anthropic": "sk-ant-real"}
    assert "unknown_provider" not in result


# ── GET /api/v1/settings ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_settings_defaults(auth_client):
    """Default settings returned when user has no profile or byok keys."""
    resp = await auth_client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["default_quality_profile"] == "balanced"
    assert data["byok_providers"] == []
    assert data["byok_key_previews"] == {}


@pytest.mark.asyncio
async def test_get_settings_with_quality_profile(mock_redis, mock_db):
    """Returns stored quality profile from user.profile."""
    user = _make_user(profile={"app_settings": {"default_quality_profile": "quality"}})
    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        resp = await c.get("/api/v1/settings")
    app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["default_quality_profile"] == "quality"


# ── PATCH /api/v1/settings ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_quality_profile(auth_client):
    """PATCH updates quality_profile and returns new settings."""
    resp = await auth_client.patch("/api/v1/settings", json={"default_quality_profile": "budget"})
    assert resp.status_code == 200
    assert resp.json()["default_quality_profile"] == "budget"


@pytest.mark.asyncio
async def test_patch_invalid_profile(auth_client):
    """Invalid quality profile value returns 422."""
    resp = await auth_client.patch("/api/v1/settings", json={"default_quality_profile": "premium"})
    assert resp.status_code == 422


# ── POST /api/v1/settings/byok ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_post_byok_stores_keys(auth_client, user):
    """POST /byok stores encrypted keys and returns masked previews."""
    resp = await auth_client.post(
        "/api/v1/settings/byok",
        json={"anthropic": "sk-ant-api03-testkey", "deepgram": "dg_test_key_abc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Providers stored
    assert "anthropic" in data["byok_providers"]
    assert "deepgram" in data["byok_providers"]
    # Previews are masked (never return full key)
    assert data["byok_key_previews"]["anthropic"] != "sk-ant-api03-testkey"
    assert "..." in data["byok_key_previews"]["anthropic"]
    # Keys are actually encrypted on the user model
    assert user.byok_keys is not None
    assert "anthropic" in user.byok_keys
    assert user.byok_keys["anthropic"] != "sk-ant-api03-testkey"


@pytest.mark.asyncio
async def test_post_byok_empty_string_removes_key(auth_client, user, mock_redis, mock_db):
    """Empty string for a provider removes that key."""
    from app.config import settings as app_settings
    from app.services.byok import encrypt_api_key

    # Pre-populate the user with an anthropic key
    enc = encrypt_api_key("sk-ant-existing", app_settings.secret_key)
    user.byok_keys = {"anthropic": enc}

    resp = await auth_client.post("/api/v1/settings/byok", json={"anthropic": ""})
    assert resp.status_code == 200
    # anthropic should be gone
    assert "anthropic" not in resp.json()["byok_providers"]


# ── DELETE /api/v1/settings/byok ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_byok_clears_all_keys(auth_client, user):
    """DELETE /byok sets byok_keys to None and returns empty providers."""
    from app.config import settings as app_settings
    from app.services.byok import encrypt_api_key

    user.byok_keys = {"anthropic": encrypt_api_key("sk-ant-test", app_settings.secret_key)}
    resp = await auth_client.delete("/api/v1/settings/byok")
    assert resp.status_code == 200
    data = resp.json()
    assert data["byok_providers"] == []
    assert user.byok_keys is None


@pytest.mark.asyncio
async def test_delete_account_returns_204(mock_redis, mock_db, user) -> None:
    """DELETE /account permanently deletes the user and all data → 204."""
    import uuid as _uuid

    # session_ids query returns one session
    session_row = MagicMock()
    session_row.__iter__ = lambda self: iter([_uuid.uuid4()])
    session_ids_result = MagicMock()
    session_ids_result.__iter__ = lambda self: iter([session_row])

    # All subsequent delete executes return a generic result
    delete_result = MagicMock()

    mock_db.execute = AsyncMock(side_effect=[session_ids_result] + [delete_result] * 8)

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/v1/settings/account")
        assert resp.status_code == 204
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_account_no_sessions_returns_204(mock_redis, mock_db, user) -> None:
    """DELETE /account when user has no sessions skips child-table deletes → 204."""
    # session_ids query returns empty (no sessions)
    empty_result = MagicMock()
    empty_result.__iter__ = lambda self: iter([])

    delete_result = MagicMock()

    mock_db.execute = AsyncMock(side_effect=[empty_result] + [delete_result] * 5)

    app.dependency_overrides[get_redis] = lambda: mock_redis
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            resp = await c.delete("/api/v1/settings/account")
        assert resp.status_code == 204
    finally:
        app.dependency_overrides.clear()
