"""Deepgram Aura TTS provider — budget option.

Used in Budget quality profile.
Cost: $0.015 per 1K characters (4x cheaper than ElevenLabs).
Same Deepgram ecosystem as STT — single API key.

Output: MP3 audio streamed in chunks for low latency.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.services.voice.interfaces import TTSProvider
from app.services.voice.types import TTSMetrics

logger = structlog.get_logger(__name__)

_DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"
_DEFAULT_MODEL = "aura-asteria-en"
_CHUNK_SIZE = 8192  # Stream in 8KB chunks for low TTFB


class DeepgramTTSProvider(TTSProvider):
    """Deepgram Aura budget TTS with streaming response.

    Streams audio bytes as they arrive from Deepgram API.
    """

    def __init__(self, api_key: str, model: str = _DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model
        self._last_metrics: TTSMetrics | None = None

    async def synthesize_stream(  # type: ignore[override]
        self,
        text: str,
    ) -> AsyncGenerator[bytes]:
        """Stream TTS audio from Deepgram in chunks."""
        start = time.monotonic()
        characters = len(text)
        first_byte_ms = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST",
                _DEEPGRAM_TTS_URL,
                params={"model": self._model},
                headers={
                    "Authorization": f"Token {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=_CHUNK_SIZE):
                    if first_byte_ms == 0:
                        first_byte_ms = int((time.monotonic() - start) * 1000)
                    yield chunk

        total_ms = int((time.monotonic() - start) * 1000)
        self._last_metrics = TTSMetrics(
            first_byte_ms=first_byte_ms,
            total_latency_ms=total_ms,
            characters=characters,
        )
        logger.debug(
            "deepgram_tts.complete",
            model=self._model,
            latency_ms=total_ms,
            first_byte_ms=first_byte_ms,
            chars=characters,
        )

    async def get_last_metrics(self) -> TTSMetrics:
        if self._last_metrics is None:
            raise RuntimeError("No TTS synthesis has been performed yet")
        return self._last_metrics
