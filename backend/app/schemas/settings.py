"""Pydantic schemas for user settings and BYOK endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SettingsResponse(BaseModel):
    """Current user settings returned by GET /api/v1/settings."""

    default_quality_profile: str
    email_digest: bool = Field(
        default=False,
        description="Whether the user has opted into weekly digest emails.",
    )
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model to use when an OpenAI BYOK key is active. "
        "Accepts any valid OpenAI model name (e.g. gpt-4o, gpt-4o-mini, o3, gpt-5).",
    )
    byok_providers: list[str] = Field(
        default_factory=list,
        description="List of providers for which the user has stored BYOK keys.",
    )
    byok_key_previews: dict[str, str] = Field(
        default_factory=dict,
        description="Masked key previews keyed by provider name (e.g. 'sk-ant-...abcd').",
    )


class SettingsPatch(BaseModel):
    """Body for PATCH /api/v1/settings."""

    default_quality_profile: str | None = Field(None, pattern="^(quality|balanced|budget)$")
    email_digest: bool | None = Field(
        None, description="Opt in (true) or out (false) of weekly digest emails."
    )
    openai_model: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="OpenAI model name to use when OpenAI BYOK key is active.",
    )


class ByokUpdate(BaseModel):
    """Body for POST /api/v1/settings/byok.

    Supply only the keys you want to add or update. Omitted providers are unchanged.
    Send an empty string for a provider to remove just that key.
    """

    anthropic: str | None = Field(None, description="Anthropic API key (sk-ant-...)")
    openai: str | None = Field(None, description="OpenAI API key (sk-...)")
    deepgram: str | None = Field(None, description="Deepgram API key (Token ...)")
    elevenlabs: str | None = Field(None, description="ElevenLabs API key")
