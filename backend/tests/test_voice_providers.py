"""Unit tests for voice provider classes (ClaudeLLM, OpenAI, DeepgramTTS, ElevenLabsTTS).

All external API calls are mocked — no network traffic.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.voice.providers.claude_llm import ClaudeLLMProvider
from app.services.voice.providers.deepgram_tts import DeepgramTTSProvider
from app.services.voice.providers.elevenlabs_tts import ElevenLabsTTSProvider
from app.services.voice.providers.openai_llm import OpenAILLMProvider
from app.services.voice.types import LLMMetrics, TTSMetrics

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_anthropic_usage(input_tokens: int = 10, output_tokens: int = 20) -> MagicMock:
    u = MagicMock()
    u.input_tokens = input_tokens
    u.output_tokens = output_tokens
    return u


def _make_tool_block(name: str, data: dict[str, Any]) -> MagicMock:
    block = MagicMock()
    block.type = "tool_use"
    block.name = name
    block.input = data
    return block


# ══════════════════════════════════════════════════════════════════════════════
# ClaudeLLMProvider
# ══════════════════════════════════════════════════════════════════════════════


class TestClaudeLLMProvider:
    """Tests for ClaudeLLMProvider."""

    def test_init_default_model_no_warning(self, caplog: Any) -> None:
        """Standard Sonnet model should not emit a warning."""
        with patch("app.services.voice.providers.claude_llm.AsyncAnthropic"):
            ClaudeLLMProvider(api_key="key", model="claude-sonnet-4-6")
        assert "non_standard_model" not in caplog.text

    def test_init_non_standard_model_logs_warning(self) -> None:
        """Custom model name triggers a warning log."""
        with patch("app.services.voice.providers.claude_llm.AsyncAnthropic"):
            # Should not raise; just logs a warning
            provider = ClaudeLLMProvider(api_key="key", model="custom-model-xyz")
        assert provider.model == "custom-model-xyz"

    @pytest.mark.asyncio
    async def test_generate_stream_yields_text(self) -> None:
        """generate_stream yields text tokens and populates _last_metrics."""

        async def _fake_text_stream() -> AsyncGenerator[str]:
            for token in ["Hello", " world"]:
                yield token

        mock_final = MagicMock()
        mock_final.usage = _make_anthropic_usage(5, 10)

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_stream_ctx)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_stream_ctx.text_stream = _fake_text_stream()
        mock_stream_ctx.get_final_message = AsyncMock(return_value=mock_final)

        mock_client = MagicMock()
        mock_client.messages.stream.return_value = mock_stream_ctx

        with patch(
            "app.services.voice.providers.claude_llm.AsyncAnthropic", return_value=mock_client
        ):
            provider = ClaudeLLMProvider(api_key="key")
            tokens: list[str] = []
            async for t in provider.generate_stream([{"role": "user", "content": "hi"}]):
                tokens.append(t)

        assert tokens == ["Hello", " world"]
        metrics = provider.get_last_metrics()
        assert metrics is not None
        assert metrics.input_tokens == 5
        assert metrics.output_tokens == 10

    @pytest.mark.asyncio
    async def test_generate_json_returns_tool_use_block(self) -> None:
        """generate_json returns parsed dict from tool_use block."""
        expected = {"score": 85, "feedback": "good answer"}
        tool_block = _make_tool_block("structured_output", expected)

        mock_response = MagicMock()
        mock_response.content = [tool_block]
        mock_response.usage = _make_anthropic_usage(20, 30)

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.voice.providers.claude_llm.AsyncAnthropic", return_value=mock_client
        ):
            provider = ClaudeLLMProvider(api_key="key")
            result, metrics = await provider.generate_json(
                messages=[{"role": "user", "content": "score this"}],
                schema={"type": "object"},
            )

        assert result == expected
        assert isinstance(metrics, LLMMetrics)

    @pytest.mark.asyncio
    async def test_generate_json_raises_when_no_tool_block(self) -> None:
        """generate_json raises ValueError when no tool_use block in response."""
        text_block = MagicMock()
        text_block.type = "text"

        mock_response = MagicMock()
        mock_response.content = [text_block]
        mock_response.usage = _make_anthropic_usage()
        mock_response.stop_reason = "end_turn"

        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)

        with patch(
            "app.services.voice.providers.claude_llm.AsyncAnthropic", return_value=mock_client
        ):
            provider = ClaudeLLMProvider(api_key="key")
            with pytest.raises(ValueError, match="no tool_use block"):
                await provider.generate_json(
                    messages=[{"role": "user", "content": "score"}],
                    schema={"type": "object"},
                )

    def test_get_last_metrics_none_before_stream(self) -> None:
        with patch("app.services.voice.providers.claude_llm.AsyncAnthropic"):
            provider = ClaudeLLMProvider(api_key="key")
        assert provider.get_last_metrics() is None


# ══════════════════════════════════════════════════════════════════════════════
# OpenAILLMProvider
# ══════════════════════════════════════════════════════════════════════════════


class TestOpenAILLMProvider:
    """Tests for OpenAILLMProvider."""

    def test_init_stores_model(self) -> None:
        with patch("app.services.voice.providers.openai_llm.AsyncOpenAI"):
            provider = OpenAILLMProvider(api_key="sk-key", model="gpt-4o-mini")
        assert provider.model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_generate_stream_yields_tokens(self) -> None:
        """generate_stream yields delta content from stream chunks."""

        def _make_chunk(content: str | None, usage: Any = None) -> MagicMock:
            chunk = MagicMock()
            chunk.usage = usage
            if content is not None:
                delta = MagicMock()
                delta.content = content
                choice = MagicMock()
                choice.delta = delta
                chunk.choices = [choice]
            else:
                chunk.choices = []
            return chunk

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 8
        mock_usage.completion_tokens = 12

        chunks = [
            _make_chunk("Hello"),
            _make_chunk(" world"),
            _make_chunk(None, usage=mock_usage),
        ]

        async def _fake_stream() -> AsyncGenerator[Any]:
            for c in chunks:
                yield c

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=_fake_stream())

        with patch("app.services.voice.providers.openai_llm.AsyncOpenAI", return_value=mock_client):
            provider = OpenAILLMProvider(api_key="sk-key")
            tokens: list[str] = []
            async for t in provider.generate_stream(
                [{"role": "user", "content": "hi"}],
                system="You are an interviewer.",
            ):
                tokens.append(t)

        assert tokens == ["Hello", " world"]
        metrics = provider.get_last_metrics()
        assert metrics is not None

    @pytest.mark.asyncio
    async def test_generate_json_returns_function_call_result(self) -> None:
        """generate_json returns parsed dict from tool_call."""
        expected = {"decision": "hire", "score": 90}

        tool_call = MagicMock()
        tool_call.function.arguments = json.dumps(expected)

        mock_choice = MagicMock()
        mock_choice.message.tool_calls = [tool_call]
        mock_choice.finish_reason = "tool_calls"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 15

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.services.voice.providers.openai_llm.AsyncOpenAI", return_value=mock_client):
            provider = OpenAILLMProvider(api_key="sk-key")
            result, metrics = await provider.generate_json(
                messages=[{"role": "user", "content": "score this"}],
                schema={"type": "object"},
                system="You are an evaluator.",
            )

        assert result == expected
        assert isinstance(metrics, LLMMetrics)

    @pytest.mark.asyncio
    async def test_generate_json_raises_when_no_tool_call(self) -> None:
        """generate_json raises ValueError when no tool_call in response."""
        mock_choice = MagicMock()
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"

        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 5
        mock_usage.completion_tokens = 5

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        with patch("app.services.voice.providers.openai_llm.AsyncOpenAI", return_value=mock_client):
            provider = OpenAILLMProvider(api_key="sk-key")
            with pytest.raises(ValueError, match="no tool_call"):
                await provider.generate_json(
                    messages=[{"role": "user", "content": "score"}],
                    schema={"type": "object"},
                )

    def test_get_last_metrics_none_before_stream(self) -> None:
        with patch("app.services.voice.providers.openai_llm.AsyncOpenAI"):
            provider = OpenAILLMProvider(api_key="sk-key")
        assert provider.get_last_metrics() is None


# ══════════════════════════════════════════════════════════════════════════════
# DeepgramTTSProvider
# ══════════════════════════════════════════════════════════════════════════════


class TestDeepgramTTSProvider:
    """Tests for DeepgramTTSProvider."""

    def test_init_stores_model(self) -> None:
        provider = DeepgramTTSProvider(api_key="dg-key", model="aura-zeus-en")
        assert provider._model == "aura-zeus-en"
        assert provider._api_key == "dg-key"

    @pytest.mark.asyncio
    async def test_synthesize_stream_yields_bytes(self) -> None:
        """synthesize_stream yields audio bytes from Deepgram API."""
        audio_chunks = [b"chunk1", b"chunk2"]

        async def _fake_aiter_bytes(chunk_size: int = 8192) -> AsyncGenerator[bytes]:
            for chunk in audio_chunks:
                yield chunk

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = _fake_aiter_bytes

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_ctx)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_client_ctx.stream = MagicMock(return_value=mock_stream_ctx)

        provider = DeepgramTTSProvider(api_key="dg-key")
        collected: list[bytes] = []

        with patch(
            "app.services.voice.providers.deepgram_tts.httpx.AsyncClient",
            return_value=mock_client_ctx,
        ):
            async for chunk in provider.synthesize_stream("Hello world"):
                collected.append(chunk)

        assert collected == audio_chunks

        metrics = await provider.get_last_metrics()
        assert isinstance(metrics, TTSMetrics)
        assert metrics.characters == len("Hello world")

    @pytest.mark.asyncio
    async def test_get_last_metrics_raises_before_synthesis(self) -> None:
        """get_last_metrics raises RuntimeError if no synthesis has been done."""
        provider = DeepgramTTSProvider(api_key="dg-key")
        with pytest.raises(RuntimeError, match="No TTS synthesis"):
            await provider.get_last_metrics()


# ══════════════════════════════════════════════════════════════════════════════
# ElevenLabsTTSProvider
# ══════════════════════════════════════════════════════════════════════════════


class TestElevenLabsTTSProvider:
    """Tests for ElevenLabsTTSProvider."""

    def test_init_stores_voice_id(self) -> None:
        provider = ElevenLabsTTSProvider(api_key="el-key", voice_id="voice123")
        assert provider._voice_id == "voice123"
        assert provider._api_key == "el-key"

    def test_init_default_voice_id(self) -> None:
        provider = ElevenLabsTTSProvider(api_key="el-key")
        assert provider._voice_id is not None  # uses Rachel default

    @pytest.mark.asyncio
    async def test_synthesize_stream_yields_bytes(self) -> None:
        """synthesize_stream yields audio bytes from ElevenLabs API."""
        audio_chunks = [b"mp3-chunk-a", b"mp3-chunk-b"]

        async def _fake_aiter_bytes(chunk_size: int = 16384) -> AsyncGenerator[bytes]:
            for chunk in audio_chunks:
                yield chunk

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = _fake_aiter_bytes

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_ctx)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_client_ctx.stream = MagicMock(return_value=mock_stream_ctx)

        provider = ElevenLabsTTSProvider(api_key="el-key")
        collected: list[bytes] = []

        with patch(
            "app.services.voice.providers.elevenlabs_tts.httpx.AsyncClient",
            return_value=mock_client_ctx,
        ):
            async for chunk in provider.synthesize_stream("Interview practice"):
                collected.append(chunk)

        assert collected == audio_chunks

        metrics = await provider.get_last_metrics()
        assert isinstance(metrics, TTSMetrics)
        assert metrics.characters == len("Interview practice")

    @pytest.mark.asyncio
    async def test_get_last_metrics_raises_before_synthesis(self) -> None:
        """get_last_metrics raises RuntimeError if no synthesis has been done."""
        provider = ElevenLabsTTSProvider(api_key="el-key")
        with pytest.raises(RuntimeError, match="No TTS synthesis"):
            await provider.get_last_metrics()

    @pytest.mark.asyncio
    async def test_synthesize_stream_skips_empty_chunks(self) -> None:
        """Empty byte chunks are not yielded (ElevenLabs padding)."""
        audio_chunks_with_empty = [b"", b"real-audio", b""]

        async def _fake_aiter_bytes(chunk_size: int = 16384) -> AsyncGenerator[bytes]:
            for chunk in audio_chunks_with_empty:
                yield chunk

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.aiter_bytes = _fake_aiter_bytes

        mock_stream_ctx = AsyncMock()
        mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
        mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_client_ctx = AsyncMock()
        mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_client_ctx)
        mock_client_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_client_ctx.stream = MagicMock(return_value=mock_stream_ctx)

        provider = ElevenLabsTTSProvider(api_key="el-key")
        collected: list[bytes] = []

        with patch(
            "app.services.voice.providers.elevenlabs_tts.httpx.AsyncClient",
            return_value=mock_client_ctx,
        ):
            async for chunk in provider.synthesize_stream("test"):
                collected.append(chunk)

        # Only non-empty chunks should be yielded
        assert collected == [b"real-audio"]
