"""Settings endpoints — user preferences and BYOK API key management.

Endpoints:
  GET    /api/v1/settings           — retrieve current settings + masked BYOK key previews
  PATCH  /api/v1/settings           — update default quality profile
  POST   /api/v1/settings/byok      — store/update encrypted BYOK keys
  DELETE /api/v1/settings/byok      — remove all BYOK keys

BYOK keys are encrypted with Fernet (SHA-256 of app secret_key) before storage.
They are NEVER returned in plaintext and NEVER logged.
"""

from __future__ import annotations

from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database import get_db
from app.models.interview_session import InterviewSession
from app.models.segment_score import SegmentScore
from app.models.session_metrics import SessionMetrics
from app.models.skill_graph_node import SkillGraphNode
from app.models.story import Story
from app.models.transcript_word import TranscriptWord
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.settings import ByokUpdate, SettingsPatch, SettingsResponse
from app.services.auth.dependencies import CurrentUser
from app.services.byok import (
    SUPPORTED_PROVIDERS,
    decrypt_api_key,
    encrypt_api_key,
    mask_key,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

_DEFAULT_QUALITY_PROFILE = "balanced"
_SETTINGS_KEY = "app_settings"  # key inside user.profile JSONB


def _get_profile_settings(user_profile: dict | None) -> dict:
    """Extract the settings sub-dict from user.profile JSONB."""
    return (user_profile or {}).get(_SETTINGS_KEY, {})


# ── GET /api/v1/settings ──────────────────────────────────────────────────────


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: CurrentUser,
) -> SettingsResponse:
    """Return current user settings and masked BYOK key previews."""
    profile_settings = _get_profile_settings(current_user.profile)
    quality_profile = profile_settings.get("default_quality_profile", _DEFAULT_QUALITY_PROFILE)

    byok_providers: list[str] = []
    byok_key_previews: dict[str, str] = {}

    if current_user.byok_keys:
        for provider, encrypted in current_user.byok_keys.items():
            if provider not in SUPPORTED_PROVIDERS:
                continue
            plaintext = decrypt_api_key(encrypted, app_settings.secret_key)
            if plaintext:
                byok_providers.append(provider)
                byok_key_previews[provider] = mask_key(plaintext)

    email_digest = bool(profile_settings.get("email_digest", False))
    openai_model = profile_settings.get("openai_model", "gpt-4o")

    return SettingsResponse(
        default_quality_profile=quality_profile,
        email_digest=email_digest,
        openai_model=openai_model,
        byok_providers=sorted(byok_providers),
        byok_key_previews=byok_key_previews,
    )


# ── PATCH /api/v1/settings ────────────────────────────────────────────────────


@router.patch("", response_model=SettingsResponse)
async def update_settings(
    body: SettingsPatch,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsResponse:
    """Update user preferences (currently: default quality profile)."""
    profile = dict(current_user.profile) if current_user.profile else {}
    profile_settings = dict(profile.get(_SETTINGS_KEY, {}))

    if body.default_quality_profile is not None:
        profile_settings["default_quality_profile"] = body.default_quality_profile
    if body.email_digest is not None:
        profile_settings["email_digest"] = body.email_digest
    if body.openai_model is not None:
        profile_settings["openai_model"] = body.openai_model

    profile[_SETTINGS_KEY] = profile_settings
    current_user.profile = profile
    await db.commit()

    logger.info(
        "settings.updated",
        user_id=str(current_user.id),
        quality_profile=profile_settings.get("default_quality_profile"),
        email_digest=profile_settings.get("email_digest"),
    )

    # Re-use GET to build the response
    return await get_settings(current_user)


# ── POST /api/v1/settings/byok ───────────────────────────────────────────────


@router.post("/byok", response_model=SettingsResponse, status_code=status.HTTP_200_OK)
async def upsert_byok_keys(
    body: ByokUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsResponse:
    """Store or update BYOK API keys (encrypted at rest).

    Send only the providers you want to update. Pass an empty string to remove
    a single provider key. Omit a provider field to leave it unchanged.
    """
    byok: dict[str, str] = dict(current_user.byok_keys) if current_user.byok_keys else {}
    changed_providers: list[str] = []

    updates = {
        "anthropic": body.anthropic,
        "openai": body.openai,
        "deepgram": body.deepgram,
        "elevenlabs": body.elevenlabs,
    }

    for provider, raw_key in updates.items():
        if raw_key is None:
            # Not supplied — leave unchanged
            continue
        if raw_key == "":
            # Explicit empty string → remove this provider's key
            byok.pop(provider, None)
            changed_providers.append(f"-{provider}")
        else:
            byok[provider] = encrypt_api_key(raw_key, app_settings.secret_key)
            changed_providers.append(f"+{provider}")

    current_user.byok_keys = byok or None  # store None if dict is now empty
    await db.commit()

    logger.info(
        "settings.byok_updated",
        user_id=str(current_user.id),
        changes=changed_providers,
    )

    return await get_settings(current_user)


# ── POST /api/v1/settings/byok/test ─────────────────────────────────────────


class ByokTestRequest(BaseModel):
    provider: str
    key: str


class ByokTestResponse(BaseModel):
    ok: bool
    message: str


@router.post("/byok/test", response_model=ByokTestResponse)
async def test_byok_key(
    body: ByokTestRequest,
    _: CurrentUser,
) -> ByokTestResponse:
    """Validate a BYOK API key by making a lightweight test call to the provider."""
    provider = body.provider.lower()
    key = body.key.strip()

    if not key:
        return ByokTestResponse(ok=False, message="No key provided.")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if provider == "anthropic":
                r = await client.get(
                    "https://api.anthropic.com/v1/models",
                    headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                )
                ok = r.status_code == 200
                message = (
                    "Connected successfully." if ok else f"Invalid key (HTTP {r.status_code})."
                )

            elif provider == "openai":
                r = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                ok = r.status_code == 200
                message = (
                    "Connected successfully." if ok else f"Invalid key (HTTP {r.status_code})."
                )

            elif provider == "deepgram":
                r = await client.get(
                    "https://api.deepgram.com/v1/projects",
                    headers={"Authorization": f"Token {key}"},
                )
                ok = r.status_code == 200
                message = (
                    "Connected successfully." if ok else f"Invalid key (HTTP {r.status_code})."
                )

            elif provider == "elevenlabs":
                r = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": key},
                )
                ok = r.status_code == 200
                message = (
                    "Connected successfully." if ok else f"Invalid key (HTTP {r.status_code})."
                )

            else:
                return ByokTestResponse(ok=False, message=f"Unknown provider: {provider}.")

    except httpx.TimeoutException:
        return ByokTestResponse(ok=False, message="Connection timed out.")
    except Exception:
        return ByokTestResponse(ok=False, message="Connection failed.")

    logger.info("settings.byok_test", provider=provider, ok=ok)
    return ByokTestResponse(ok=ok, message=message)


# ── DELETE /api/v1/settings/account ──────────────────────────────────────────


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Permanently delete the authenticated user and all associated data (GDPR erasure).

    Deletion order respects FK constraints:
    transcript_words → segment_scores → session_metrics → sessions
    → skill_graph → stories → usage_logs → user
    """
    uid = current_user.id

    # Collect session IDs for child-table deletes that FK on session_id
    session_ids_result = await db.execute(
        InterviewSession.__table__.select()
        .with_only_columns(  # type: ignore[attr-defined]
            InterviewSession.id
        )
        .where(InterviewSession.user_id == uid)
    )
    session_ids = [row[0] for row in session_ids_result]

    if session_ids:
        await db.execute(delete(TranscriptWord).where(TranscriptWord.session_id.in_(session_ids)))
        await db.execute(delete(SegmentScore).where(SegmentScore.session_id.in_(session_ids)))
        await db.execute(delete(SessionMetrics).where(SessionMetrics.session_id.in_(session_ids)))

    await db.execute(delete(InterviewSession).where(InterviewSession.user_id == uid))
    await db.execute(delete(SkillGraphNode).where(SkillGraphNode.user_id == uid))
    await db.execute(delete(Story).where(Story.user_id == uid))
    await db.execute(delete(UsageLog).where(UsageLog.user_id == uid))
    await db.execute(delete(User).where(User.id == uid))
    await db.commit()

    logger.info("account.deleted", user_id=str(uid))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ── DELETE /api/v1/settings/byok ─────────────────────────────────────────────


@router.delete("/byok", response_model=SettingsResponse, status_code=status.HTTP_200_OK)
async def delete_byok_keys(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SettingsResponse:
    """Remove ALL stored BYOK API keys."""
    current_user.byok_keys = None
    await db.commit()

    logger.info("settings.byok_deleted", user_id=str(current_user.id))
    return await get_settings(current_user)
