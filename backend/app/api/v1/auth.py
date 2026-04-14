"""Auth endpoints: register, login, refresh, me, google (stub).

Security:
- bcrypt(12) for passwords
- JWT 15-min access + 7-day refresh (httpOnly cookie)
- 5 failed logins → 15-min lockout
- 5 req/min per IP rate limit on all auth endpoints
"""

import typing
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from jose import JWTError
from pydantic import BaseModel as _BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.rate_limit import RateLimit
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    RefreshRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.auth.jwt_utils import create_access_token, create_refresh_token, decode_token
from app.services.auth.password import hash_password, verify_password

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_LOCKOUT_ATTEMPTS = 5
_LOCKOUT_MINUTES = 15
_REFRESH_COOKIE = "refresh_token"


# ── POST /register ─────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: UserCreate,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rl: RateLimit,
) -> TokenResponse:
    """Register a new user and return tokens."""
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("auth.registered", user_id=str(user.id))

    access = create_access_token(user.id, user.email, user.role.value)
    refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh)

    return TokenResponse(access_token=access)


# ── POST /login ────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(
    body: UserLogin,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rl: RateLimit,
) -> TokenResponse:
    """Authenticate user; enforce lockout after 5 failures."""
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    # Generic error — don't reveal whether email exists
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )

    if user is None:
        raise auth_error

    # Lockout check
    if user.is_locked():
        locked_until = user.locked_until or datetime.now(tz=UTC)
        remaining = int((locked_until - datetime.now(tz=UTC)).total_seconds() // 60)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked. Try again in {remaining} minute(s).",
        )

    if not user.hashed_password or not verify_password(body.password, user.hashed_password):
        # Increment failure counter
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= _LOCKOUT_ATTEMPTS:
            user.locked_until = datetime.now(tz=UTC) + timedelta(minutes=_LOCKOUT_MINUTES)
            logger.warning(
                "auth.account_locked",
                user_id=str(user.id),
                lockout_minutes=_LOCKOUT_MINUTES,
            )
        await db.commit()
        raise auth_error

    # Success — reset counter
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    logger.info("auth.login_success", user_id=str(user.id))

    access = create_access_token(user.id, user.email, user.role.value)
    refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh)

    return TokenResponse(access_token=access)


# ── POST /refresh ──────────────────────────────────────────────────────────────


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    body: RefreshRequest | None = None,
    cookie_token: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
) -> TokenResponse:
    """Issue a new access token from a valid refresh token (cookie or body)."""
    raw_token = (body.refresh_token if body else None) or cookie_token

    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
    )

    if not raw_token:
        raise invalid_exc

    try:
        payload = decode_token(raw_token)
        if payload.get("type") != "refresh":
            raise invalid_exc
        import uuid as _uuid

        user_id = _uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise invalid_exc

    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise invalid_exc

    access = create_access_token(user.id, user.email, user.role.value)
    new_refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, new_refresh)

    return TokenResponse(access_token=access)


# ── GET /me ────────────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def me(current_user: CurrentUser) -> UserResponse:
    """Return the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


# ── POST /google ───────────────────────────────────────────────────────────────


class GoogleAuthRequest(_BaseModel):
    id_token: str


@router.post("/google", response_model=TokenResponse)
async def google_oauth(
    body: GoogleAuthRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Verify a Google ID token and create/login the user.

    Frontend sends the id_token from Google Sign-In.
    We verify it with Google's tokeninfo endpoint, extract email/sub,
    and either find or create the user.
    """
    import httpx

    # Verify the token with Google
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": body.id_token},
            )
    except Exception as exc:
        logger.error("auth.google_verify_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="Failed to verify Google token")

    if resp.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    google_data = resp.json()
    email = google_data.get("email")
    google_id = google_data.get("sub")

    if not email or not google_id:
        raise HTTPException(status_code=401, detail="Google token missing email or sub")

    # Find existing user by google_id or email
    result = await db.execute(
        select(User).where((User.google_id == google_id) | (User.email == email))
    )
    user = result.scalar_one_or_none()

    if user is None:
        # Create new user (no password — OAuth only)
        user = User(email=email, google_id=google_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("auth.google_registered", user_id=str(user.id))
    else:
        # Link google_id if not already set
        if not user.google_id:
            user.google_id = google_id
            await db.commit()
        logger.info("auth.google_login", user_id=str(user.id))

    access = create_access_token(user.id, user.email, user.role.value)
    refresh = create_refresh_token(user.id)
    _set_refresh_cookie(response, refresh)

    return TokenResponse(access_token=access)


# ── POST /forgot-password ──────────────────────────────────────────────────────


def _create_reset_token(user_id: str) -> str:
    """Create a short-lived JWT for password reset (30 min)."""
    from jose import jwt as _jwt

    from app.config import settings as _settings

    expire = datetime.now(tz=UTC) + timedelta(minutes=30)
    payload = {"sub": user_id, "type": "password_reset", "exp": expire}
    return _jwt.encode(payload, _settings.secret_key, algorithm=_settings.jwt_algorithm)


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    body: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rl: RateLimit,
) -> dict[str, typing.Any]:
    """Request a password reset.

    Always returns 200 regardless of whether the email exists (security best practice).
    In production, sends an email with the reset link. For now, returns the token
    in the response for development/testing.
    """
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    # Always return the same response to avoid email enumeration
    response_msg = {
        "message": "If an account with that email exists, a password reset link has been sent."
    }

    if user is None or not user.is_active:
        logger.info("auth.forgot_password_unknown_email")
        return response_msg

    if not user.hashed_password:
        # OAuth-only user — can't reset password
        logger.info("auth.forgot_password_oauth_user", user_id=str(user.id))
        return response_msg

    token = _create_reset_token(str(user.id))

    # In production: send email with reset link
    # For dev: log the token so it can be used
    logger.info("auth.password_reset_requested", user_id=str(user.id))

    try:
        from app.config import settings as _settings
        from app.services.email import send_email

        if _settings.smtp_host:
            reset_url = f"{_settings.cors_origins[0] if _settings.cors_origins else 'http://localhost:3000'}/reset-password?token={token}"
            await send_email(
                to_email=user.email,
                subject="InterviewCraft — Password Reset",
                config=_settings,
                html_body=f"""
                <div style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
                    <h2 style="color: #1e293b;">Reset your password</h2>
                    <p style="color: #475569;">Click the button below to reset your password. This link expires in 30 minutes.</p>
                    <a href="{reset_url}" style="display: inline-block; padding: 12px 24px; background: #6366f1; color: white; text-decoration: none; border-radius: 8px; font-weight: 600; margin: 16px 0;">
                        Reset Password
                    </a>
                    <p style="color: #94a3b8; font-size: 12px;">If you didn't request this, ignore this email.</p>
                </div>
                """,
            )
    except Exception as exc:
        logger.warning("auth.reset_email_send_failed", error=str(exc))

    # In dev mode, include token in response for testing
    from app.config import settings as _settings

    if _settings.app_env in ("development", "test"):
        response_msg["reset_token"] = token

    return response_msg


# ── POST /reset-password ──────────────────────────────────────────────────────


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    body: ResetPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _rl: RateLimit,
) -> dict[str, typing.Any]:
    """Reset the user's password using a valid reset token."""
    try:
        payload = decode_token(body.token)
        if payload.get("type") != "password_reset":
            raise HTTPException(status_code=400, detail="Invalid reset token")
        import uuid as _uuid

        user_id = _uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user.hashed_password = hash_password(body.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    logger.info("auth.password_reset_complete", user_id=str(user.id))

    return {"message": "Password has been reset successfully. You can now sign in."}


# ── Helpers ────────────────────────────────────────────────────────────────────


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Attach the refresh token as an httpOnly cookie.

    Production uses SameSite=None (required for cross-origin requests when the
    frontend is on Vercel and the API is on Fly.io).  SameSite=None mandates
    Secure=True, which is already enforced in production.

    Development uses SameSite=Lax so the cookie works on localhost without HTTPS.
    """
    is_production = settings.app_env == "production"
    response.set_cookie(
        key=_REFRESH_COOKIE,
        value=token,
        httponly=True,
        samesite="none" if is_production else "lax",
        secure=is_production,
        max_age=7 * 24 * 60 * 60,
    )
