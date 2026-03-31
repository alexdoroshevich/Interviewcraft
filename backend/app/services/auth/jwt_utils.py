"""JWT creation and verification.

Access token:  15 min, returned in response body (Bearer).
Refresh token: 7 days, set as httpOnly cookie.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt

from app.config import settings


def _now_utc() -> datetime:
    return datetime.now(tz=UTC)


def create_access_token(user_id: uuid.UUID, email: str, role: str) -> str:
    """Return a signed JWT access token (15-min expiry)."""
    expire = _now_utc() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Return a signed JWT refresh token (7-day expiry, includes jti for future revocation)."""
    expire = _now_utc() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT.  Raises JWTError on invalid / expired token."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
