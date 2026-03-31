"""Unit tests for ProviderFactory — all three quality profiles + BYOK paths."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.services.voice.interfaces import ProviderSet
from app.services.voice.provider_factory import ProviderFactory


def _mock_settings(
    *,
    deepgram_key: str = "dg-key",
    anthropic_key: str = "ant-key",
    elevenlabs_key: str = "el-key",
) -> MagicMock:
    s = MagicMock()
    s.deepgram_api_key = deepgram_key
    s.anthropic_api_key = anthropic_key
    s.elevenlabs_api_key = elevenlabs_key
    return s


# ── Patch all heavy provider __init__ calls ───────────────────────────────────

_PATCH_DEEPGRAM_STT = "app.services.voice.provider_factory.DeepgramSTTProvider"
_PATCH_DEEPGRAM_TTS = "app.services.voice.provider_factory.DeepgramTTSProvider"
_PATCH_ELEVENLABS = "app.services.voice.provider_factory.ElevenLabsTTSProvider"
_PATCH_CLAUDE = "app.services.voice.provider_factory.ClaudeLLMProvider"
_PATCH_OPENAI = "app.services.voice.provider_factory.OpenAILLMProvider"


def _make_provider_mock(model: str = "test-model") -> MagicMock:
    m = MagicMock()
    m.model = model
    return m


# ── Quality profile ───────────────────────────────────────────────────────────


def test_quality_profile_uses_elevenlabs_tts() -> None:
    """Quality profile: primary LLM everywhere + ElevenLabs TTS."""
    settings = _mock_settings()
    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()) as mock_stt,
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()) as mock_el,
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, return_value=_make_provider_mock("claude-sonnet-4-6")),
    ):
        result = ProviderFactory.create("quality", settings)

    assert isinstance(result, ProviderSet)
    mock_stt.assert_called_once_with(api_key="dg-key")
    # ElevenLabs should be called (quality profile uses it)
    mock_el.assert_called_once()
    # All LLMs are the same primary instance for quality
    assert result.voice_llm is result.scoring_llm
    assert result.voice_llm is result.diff_llm
    assert result.voice_llm is result.memory_llm


def test_quality_profile_stores_profile_name() -> None:
    settings = _mock_settings()
    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, return_value=_make_provider_mock("claude-sonnet-4-6")),
    ):
        result = ProviderFactory.create("quality", settings)

    assert result.quality_profile == "quality"


# ── Balanced profile ──────────────────────────────────────────────────────────


def test_balanced_profile_splits_primary_secondary() -> None:
    """Balanced: primary (Sonnet) for voice_llm, secondary (Haiku) for scoring."""
    settings = _mock_settings()
    primary = _make_provider_mock("claude-sonnet-4-6")
    secondary = _make_provider_mock("claude-haiku-4-5-20251001")

    call_count = 0

    def _make_claude(api_key: str, model: str) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if model == "claude-sonnet-4-6":
            return primary
        return secondary

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, side_effect=_make_claude),
    ):
        result = ProviderFactory.create("balanced", settings)

    assert result.voice_llm is primary
    assert result.scoring_llm is secondary
    assert result.diff_llm is secondary
    assert result.memory_llm is secondary
    assert result.quality_profile == "balanced"


# ── Budget profile ────────────────────────────────────────────────────────────


def test_budget_profile_uses_deepgram_tts() -> None:
    """Budget profile: Haiku everywhere + Deepgram Aura TTS."""
    settings = _mock_settings()
    haiku = _make_provider_mock("claude-haiku-4-5-20251001")
    dg_tts = MagicMock()

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=dg_tts) as mock_dg_tts,
        patch(_PATCH_CLAUDE, return_value=haiku),
    ):
        result = ProviderFactory.create("budget", settings)

    assert result.tts is dg_tts
    assert result.quality_profile == "budget"
    mock_dg_tts.assert_called_once()


def test_budget_profile_aura_voice_id_passed_to_deepgram_tts() -> None:
    """Budget + aura- voice_id: Deepgram TTS should receive the model kwarg."""
    settings = _mock_settings()

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()) as mock_dg_tts,
        patch(_PATCH_CLAUDE, return_value=_make_provider_mock("claude-haiku-4-5-20251001")),
    ):
        ProviderFactory.create("budget", settings, voice_id="aura-zeus-en")

    call_kwargs = mock_dg_tts.call_args
    # model kwarg should be set to the aura voice id
    assert call_kwargs.kwargs.get("model") == "aura-zeus-en" or (
        len(call_kwargs.args) >= 2 and call_kwargs.args[1] == "aura-zeus-en"
    )


# ── BYOK keys ─────────────────────────────────────────────────────────────────


def test_byok_anthropic_key_overrides_platform_key() -> None:
    """BYOK anthropic key takes precedence over platform key."""
    settings = _mock_settings(anthropic_key="platform-ant-key")

    captured_keys: list[str] = []

    def _capture_claude(api_key: str, model: str) -> MagicMock:
        captured_keys.append(api_key)
        return _make_provider_mock(model)

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, side_effect=_capture_claude),
    ):
        ProviderFactory.create("balanced", settings, byok_keys={"anthropic": "byok-ant-key"})

    # All Claude instances should use the BYOK key
    assert all(k == "byok-ant-key" for k in captured_keys)


def test_byok_deepgram_key_used_for_stt() -> None:
    """BYOK deepgram key takes precedence for STT."""
    settings = _mock_settings(deepgram_key="platform-dg-key")

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()) as mock_stt,
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, return_value=_make_provider_mock("claude-sonnet-4-6")),
    ):
        ProviderFactory.create("quality", settings, byok_keys={"deepgram": "byok-dg-key"})

    mock_stt.assert_called_once_with(api_key="byok-dg-key")


def test_byok_elevenlabs_key_used_for_tts() -> None:
    """BYOK elevenlabs key passed to ElevenLabsTTSProvider."""
    settings = _mock_settings(elevenlabs_key="platform-el-key")

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()) as mock_el,
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, return_value=_make_provider_mock("claude-sonnet-4-6")),
    ):
        ProviderFactory.create("quality", settings, byok_keys={"elevenlabs": "byok-el-key"})

    call_kwargs = mock_el.call_args
    assert call_kwargs.kwargs.get("api_key") == "byok-el-key"


# ── OpenAI BYOK ───────────────────────────────────────────────────────────────


def test_openai_byok_uses_openai_provider() -> None:
    """OpenAI BYOK key activates OpenAILLMProvider instead of Claude."""
    settings = _mock_settings()
    openai_primary = _make_provider_mock("gpt-4o")
    openai_secondary = _make_provider_mock("gpt-4o-mini")

    call_idx = 0

    def _make_openai(api_key: str, model: str) -> MagicMock:
        nonlocal call_idx
        call_idx += 1
        if model == "gpt-4o":
            return openai_primary
        return openai_secondary

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, return_value=MagicMock()),
        patch(_PATCH_OPENAI, side_effect=_make_openai),
    ):
        result = ProviderFactory.create(
            "balanced",
            settings,
            byok_keys={"openai": "sk-openai-key"},
        )

    assert result.voice_llm is openai_primary


def test_openai_byok_quality_profile_uses_same_model_for_secondary() -> None:
    """Quality + OpenAI: secondary model matches primary model."""
    settings = _mock_settings()
    created_models: list[str] = []

    def _make_openai(api_key: str, model: str) -> MagicMock:
        created_models.append(model)
        return _make_provider_mock(model)

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, return_value=MagicMock()),
        patch(_PATCH_OPENAI, side_effect=_make_openai),
    ):
        ProviderFactory.create(
            "quality",
            settings,
            byok_keys={"openai": "sk-openai-key"},
            openai_model="gpt-4o",
        )

    # Both primary and secondary should use same model for quality profile
    assert all(m == "gpt-4o" for m in created_models)


# ── Voice ID passthrough ──────────────────────────────────────────────────────


def test_voice_id_passed_to_elevenlabs() -> None:
    """voice_id kwarg is forwarded to ElevenLabsTTSProvider."""
    settings = _mock_settings()

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()) as mock_el,
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()),
        patch(_PATCH_CLAUDE, return_value=_make_provider_mock("claude-sonnet-4-6")),
    ):
        ProviderFactory.create("quality", settings, voice_id="21m00Tcm4TlvDq8ikWAM")

    call_kwargs = mock_el.call_args
    assert call_kwargs.kwargs.get("voice_id") == "21m00Tcm4TlvDq8ikWAM"


def test_non_aura_voice_id_not_passed_to_deepgram_tts() -> None:
    """A non-aura voice_id should not be forwarded as a model to DeepgramTTS."""
    settings = _mock_settings()

    with (
        patch(_PATCH_DEEPGRAM_STT, return_value=MagicMock()),
        patch(_PATCH_ELEVENLABS, return_value=MagicMock()),
        patch(_PATCH_DEEPGRAM_TTS, return_value=MagicMock()) as mock_dg_tts,
        patch(_PATCH_CLAUDE, return_value=_make_provider_mock("claude-haiku-4-5-20251001")),
    ):
        ProviderFactory.create("budget", settings, voice_id="rachel-voice-id")

    call_kwargs = mock_dg_tts.call_args
    # model kwarg should NOT be set for non-aura voice IDs
    assert "model" not in (call_kwargs.kwargs or {})
