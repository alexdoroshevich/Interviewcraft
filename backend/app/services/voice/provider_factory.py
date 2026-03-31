"""ProviderFactory — creates ProviderSet based on session quality_profile.

Quality profiles (from spec):
  quality:  Sonnet all tasks + ElevenLabs     (~$0.60–1.30/session)
  balanced: Sonnet voice, Haiku scoring/diff/memory + ElevenLabs  (~$0.30–0.60)
  budget:   Haiku all + Deepgram Aura-1 TTS  (~$0.15–0.30)
"""

import structlog

from app.config import Settings
from app.services.voice.interfaces import LLMProvider, ProviderSet
from app.services.voice.providers.claude_llm import ClaudeLLMProvider
from app.services.voice.providers.deepgram_stt import DeepgramSTTProvider
from app.services.voice.providers.deepgram_tts import DeepgramTTSProvider
from app.services.voice.providers.elevenlabs_tts import ElevenLabsTTSProvider
from app.services.voice.providers.openai_llm import OpenAILLMProvider

logger = structlog.get_logger(__name__)

_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-5-20251001"
_GPT4O = "gpt-4o"
_GPT4O_MINI = "gpt-4o-mini"


class ProviderFactory:
    """Factory — call ProviderFactory.create() once per session."""

    @staticmethod
    def create(
        quality_profile: str,
        settings: Settings,
        voice_id: str | None = None,
        byok_keys: dict[str, str] | None = None,
        openai_model: str = "gpt-4o",
    ) -> ProviderSet:
        """Build and return the ProviderSet for the given quality profile.

        Args:
            quality_profile: One of "quality", "balanced", or "budget".
            settings: Application settings (platform API keys).
            voice_id: Optional ElevenLabs voice ID override.
            byok_keys: Optional dict of provider → plaintext key (BYOK).
                       Supported providers: anthropic, deepgram, elevenlabs.
                       BYOK keys take precedence over platform keys when present.
        """
        byok = byok_keys or {}

        deepgram_key = byok.get("deepgram") or settings.deepgram_api_key
        anthropic_key = byok.get("anthropic") or settings.anthropic_api_key
        elevenlabs_key = byok.get("elevenlabs") or settings.elevenlabs_api_key
        openai_key = byok.get("openai")

        if byok:
            logger.info(
                "provider_factory.byok_active",
                providers=sorted(byok.keys()),
            )

        stt = DeepgramSTTProvider(api_key=deepgram_key)

        # LLM selection: OpenAI BYOK takes precedence over Claude when key is present.
        # quality/balanced → gpt-4o or sonnet; budget → gpt-4o-mini or haiku.
        primary_llm: LLMProvider
        secondary_llm: LLMProvider  # used for scoring/diff/memory in balanced profile

        if openai_key:
            # Use the user-specified model for primary. For secondary (scoring/diff/memory
            # in balanced), default to gpt-4o-mini unless the user picked a small model.
            secondary_model = openai_model if quality_profile == "quality" else _GPT4O_MINI
            primary_llm = OpenAILLMProvider(api_key=openai_key, model=openai_model)
            secondary_llm = OpenAILLMProvider(api_key=openai_key, model=secondary_model)
            logger.info(
                "provider_factory.openai_active",
                profile=quality_profile,
                model=openai_model,
            )
        else:
            primary_llm = ClaudeLLMProvider(api_key=anthropic_key, model=_SONNET)
            secondary_llm = ClaudeLLMProvider(api_key=anthropic_key, model=_HAIKU)

        # Keep Claude instances available for budget profile fallback (Haiku is cheaper)
        haiku = (
            secondary_llm if openai_key else ClaudeLLMProvider(api_key=anthropic_key, model=_HAIKU)
        )

        # Pass voice_id to ElevenLabs (uses default "Rachel" if None)
        el_kwargs: dict[str, str] = {"api_key": elevenlabs_key}
        if voice_id:
            el_kwargs["voice_id"] = voice_id
        elevenlabs = ElevenLabsTTSProvider(**el_kwargs)

        # Budget TTS: use voice_id as Deepgram Aura model if it's a Deepgram voice
        # (Deepgram voice IDs start with "aura-"); otherwise use default female voice.
        dg_tts_model = voice_id if (voice_id and voice_id.startswith("aura-")) else None
        dg_tts_kwargs: dict[str, str] = {"api_key": settings.deepgram_api_key}
        if dg_tts_model:
            dg_tts_kwargs["model"] = dg_tts_model
        deepgram_tts = DeepgramTTSProvider(**dg_tts_kwargs)

        if quality_profile == "quality":
            provider_set = ProviderSet(
                stt=stt,
                voice_llm=primary_llm,
                scoring_llm=primary_llm,
                diff_llm=primary_llm,
                memory_llm=primary_llm,
                tts=elevenlabs,
                quality_profile=quality_profile,
            )
        elif quality_profile == "balanced":
            provider_set = ProviderSet(
                stt=stt,
                voice_llm=primary_llm,
                scoring_llm=secondary_llm,
                diff_llm=secondary_llm,
                memory_llm=secondary_llm,
                tts=elevenlabs,
                quality_profile=quality_profile,
            )
        else:  # budget
            # Budget profile uses Deepgram Aura TTS (spec: ~$0.15–0.30/session)
            provider_set = ProviderSet(
                stt=stt,
                voice_llm=haiku,
                scoring_llm=haiku,
                diff_llm=haiku,
                memory_llm=haiku,
                tts=deepgram_tts,
                quality_profile=quality_profile,
            )

        logger.info(
            "provider_factory.created",
            profile=quality_profile,
            voice_llm=provider_set.voice_llm.model,  # type: ignore[attr-defined]
        )
        return provider_set
