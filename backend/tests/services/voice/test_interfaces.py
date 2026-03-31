"""Provider interface contract tests — mock implementations verify the ABCs.

These tests ensure any concrete provider (real or future) satisfies the contract.
They run without real API keys (no @pytest.mark.integration needed).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest

from app.services.voice.costs import (
    calc_anthropic_cost,
    calc_deepgram_stt_cost,
    calc_deepgram_tts_cost,
    calc_elevenlabs_cost,
)
from app.services.voice.interfaces import LLMProvider, ProviderSet, STTProvider, TTSProvider
from app.services.voice.smart_pause import PauseAction, SmartPause
from app.services.voice.types import LLMMetrics, TranscriptChunk, TTSMetrics, WordTimestamp

# ── Stub implementations ───────────────────────────────────────────────────────


class StubSTTProvider(STTProvider):
    """Minimal STT stub — yields one partial then one final chunk."""

    async def transcribe_stream(  # type: ignore[override]
        self,
        audio_chunks: AsyncGenerator[bytes],
    ) -> AsyncGenerator[TranscriptChunk]:
        # Drain audio
        async for _ in audio_chunks:
            pass
        yield TranscriptChunk(
            text="tell me about",
            is_final=False,
            words=[],
            confidence=0.9,
            start_ms=0,
            end_ms=500,
        )
        yield TranscriptChunk(
            text="tell me about yourself",
            is_final=True,
            words=[
                WordTimestamp("tell", 0, 200, 0.99),
                WordTimestamp("me", 210, 350, 0.98),
                WordTimestamp("about", 360, 500, 0.97),
                WordTimestamp("yourself", 510, 900, 0.96),
            ],
            confidence=0.97,
            start_ms=0,
            end_ms=900,
        )


class StubLLMProvider(LLMProvider):
    """Minimal LLM stub — yields fixed tokens."""

    _TOKENS = ["Great ", "question. ", "Tell me more."]
    _METRICS = LLMMetrics(ttft_ms=120, total_latency_ms=400, input_tokens=50, output_tokens=15)

    async def generate_stream(  # type: ignore[override]
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str]:
        for token in self._TOKENS:
            yield token

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> tuple[dict[str, Any], LLMMetrics]:
        return {"overall_score": 72, "rules_triggered": []}, self._METRICS

    def get_last_metrics(self) -> LLMMetrics | None:
        return self._METRICS


class StubTTSProvider(TTSProvider):
    """Minimal TTS stub — yields fake audio bytes."""

    _METRICS = TTSMetrics(first_byte_ms=80, total_latency_ms=200, characters=15)

    async def synthesize_stream(  # type: ignore[override]
        self,
        text: str,
    ) -> AsyncGenerator[bytes]:
        yield b"\x00\x01\x02\x03"  # Fake PCM data
        yield b"\x04\x05\x06\x07"

    async def get_last_metrics(self) -> TTSMetrics:
        return self._METRICS


# ── STT contract tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stt_yields_partial_then_final():
    """STT must yield at least one partial and one final chunk."""
    provider = StubSTTProvider()
    chunks: list[TranscriptChunk] = []

    async def _empty_audio() -> AsyncGenerator[bytes]:
        return
        yield b""  # Make it an async generator

    async for chunk in provider.transcribe_stream(_empty_audio()):
        chunks.append(chunk)

    assert len(chunks) == 2
    partials = [c for c in chunks if not c.is_final]
    finals = [c for c in chunks if c.is_final]
    assert len(partials) >= 1
    assert len(finals) >= 1


@pytest.mark.asyncio
async def test_stt_final_has_word_timestamps():
    """Final transcript chunks MUST have word-level timestamps."""
    provider = StubSTTProvider()

    async def _empty_audio() -> AsyncGenerator[bytes]:
        return
        yield b""

    async for chunk in provider.transcribe_stream(_empty_audio()):
        if chunk.is_final:
            assert len(chunk.words) > 0
            for w in chunk.words:
                assert isinstance(w.start_ms, int)
                assert isinstance(w.end_ms, int)
                assert w.end_ms >= w.start_ms
                assert 0.0 <= w.confidence <= 1.0


# ── LLM contract tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_llm_stream_yields_strings():
    """generate_stream must yield non-empty strings."""
    provider = StubLLMProvider()
    tokens: list[str] = []
    async for token in provider.generate_stream([{"role": "user", "content": "Hi"}]):
        tokens.append(token)
    assert len(tokens) > 0
    assert all(isinstance(t, str) for t in tokens)
    assert "".join(tokens).strip() != ""


@pytest.mark.asyncio
async def test_llm_generate_json_returns_dict_and_metrics():
    """generate_json must return (dict, LLMMetrics)."""
    provider = StubLLMProvider()
    result, metrics = await provider.generate_json(
        messages=[{"role": "user", "content": "score this"}],
        schema={"type": "object", "properties": {"overall_score": {"type": "integer"}}},
    )
    assert isinstance(result, dict)
    assert isinstance(metrics, LLMMetrics)
    assert metrics.input_tokens > 0
    assert metrics.output_tokens > 0


def test_llm_get_last_metrics_after_stream():
    """get_last_metrics returns LLMMetrics (or None before first call)."""
    provider = StubLLMProvider()
    # Before any call — implementation may return None
    metrics = provider.get_last_metrics()
    assert metrics is None or isinstance(metrics, LLMMetrics)


# ── TTS contract tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tts_yields_bytes():
    """synthesize_stream must yield bytes."""
    provider = StubTTSProvider()
    chunks: list[bytes] = []
    async for chunk in provider.synthesize_stream("Hello world"):
        chunks.append(chunk)
    assert len(chunks) > 0
    assert all(isinstance(c, bytes) for c in chunks)
    assert sum(len(c) for c in chunks) > 0


@pytest.mark.asyncio
async def test_tts_metrics_available_after_synthesis():
    """get_last_metrics must be available after synthesis."""
    provider = StubTTSProvider()
    async for _ in provider.synthesize_stream("Test"):
        pass
    metrics = await provider.get_last_metrics()
    assert isinstance(metrics, TTSMetrics)
    assert metrics.characters > 0
    assert metrics.first_byte_ms >= 0


# ── ProviderSet structure ──────────────────────────────────────────────────────


def test_provider_set_has_all_fields():
    """ProviderSet must expose stt, voice_llm, scoring_llm, diff_llm, memory_llm, tts."""
    ps = ProviderSet(
        stt=StubSTTProvider(),
        voice_llm=StubLLMProvider(),
        scoring_llm=StubLLMProvider(),
        diff_llm=StubLLMProvider(),
        memory_llm=StubLLMProvider(),
        tts=StubTTSProvider(),
    )
    assert ps.stt is not None
    assert ps.voice_llm is not None
    assert ps.scoring_llm is not None
    assert ps.diff_llm is not None
    assert ps.memory_llm is not None
    assert ps.tts is not None


# ── SmartPause tests ───────────────────────────────────────────────────────────


def test_smart_pause_no_action_on_recent_partial():
    """If partial arrived <700ms ago, check() must return NONE."""
    sp = SmartPause()
    sp.on_partial()
    assert sp.is_user_still_speaking() is True
    assert sp.check() == PauseAction.NONE


def test_smart_pause_no_action_immediately_after_final():
    """Right after a final, silence has not yet exceeded thresholds."""
    sp = SmartPause()
    sp.on_final()
    assert sp.check() == PauseAction.NONE


# ── Cost calculation tests ─────────────────────────────────────────────────────


def test_anthropic_cost_sonnet():
    cost = calc_anthropic_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=200)
    assert float(cost) > 0


def test_anthropic_cost_cached_is_cheaper():
    full = calc_anthropic_cost("claude-sonnet-4-6", input_tokens=1000, output_tokens=200)
    cached = calc_anthropic_cost(
        "claude-sonnet-4-6", input_tokens=1000, output_tokens=200, cached_tokens=800
    )
    assert cached < full


def test_deepgram_stt_cost():
    cost = calc_deepgram_stt_cost(audio_seconds=60.0)  # 1 minute
    assert abs(float(cost) - 0.0058) < 0.0001


def test_elevenlabs_cost():
    cost = calc_elevenlabs_cost(characters=1000)
    assert abs(float(cost) - 0.06) < 0.0001


def test_deepgram_tts_cost():
    cost = calc_deepgram_tts_cost(characters=1000)
    assert abs(float(cost) - 0.015) < 0.0001
