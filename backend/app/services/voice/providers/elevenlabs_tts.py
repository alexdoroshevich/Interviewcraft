"""ElevenLabs Turbo v2.5 TTS provider — streaming via httpx.

Quality TTS used in Quality and Balanced profiles.
Cost: $0.06 per 1K characters.

Uses httpx streaming directly (more reliable than SDK for async streaming).
Output: MP3 audio at 44.1kHz 128kbps, sent as bytes chunks.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator

import httpx
import structlog

from app.services.voice.interfaces import TTSProvider
from app.services.voice.types import TTSMetrics

logger = structlog.get_logger(__name__)

_ELEVENLABS_STREAM_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel — natural, neutral
_MODEL_ID = "eleven_turbo_v2_5"
_OUTPUT_FORMAT = "mp3_44100_128"  # MP3 — browser decodeAudioData needs a container format


class ElevenLabsTTSProvider(TTSProvider):
    """ElevenLabs Turbo v2.5 streaming TTS.

    Streams first audio byte while the rest generates — feeds directly into
    the WebSocket audio output without buffering the full response.
    """

    def __init__(self, api_key: str, voice_id: str = _DEFAULT_VOICE_ID) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._last_metrics: TTSMetrics | None = None

    async def synthesize_stream(  # type: ignore[override]
        self,
        text: str,
    ) -> AsyncGenerator[bytes]:
        """Yield MP3 audio bytes as they arrive from ElevenLabs."""
        start = time.monotonic()
        first_byte_ms: int | None = None
        characters = len(text)

        url = _ELEVENLABS_STREAM_URL.format(voice_id=self._voice_id)
        headers = {
            "xi-api-key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        # output_format and optimize_streaming_latency go as query params per ElevenLabs API
        params = {
            "output_format": _OUTPUT_FORMAT,
            "optimize_streaming_latency": "4",
        }
        payload = {
            "text": text,
            "model_id": _MODEL_ID,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream(
                "POST", url, headers=headers, params=params, json=payload
            ) as response:
                response.raise_for_status()
                async for chunk in response.aiter_bytes(chunk_size=16384):
                    if chunk:
                        if first_byte_ms is None:
                            first_byte_ms = int((time.monotonic() - start) * 1000)
                            logger.debug(
                                "elevenlabs_tts.first_byte",
                                first_byte_ms=first_byte_ms,
                                chars=characters,
                            )
                        yield chunk

        total_ms = int((time.monotonic() - start) * 1000)
        self._last_metrics = TTSMetrics(
            first_byte_ms=first_byte_ms or total_ms,
            total_latency_ms=total_ms,
            characters=characters,
        )
        logger.debug(
            "elevenlabs_tts.complete",
            first_byte_ms=self._last_metrics.first_byte_ms,
            total_ms=total_ms,
            chars=characters,
        )

    async def get_last_metrics(self) -> TTSMetrics:
        if self._last_metrics is None:
            raise RuntimeError("No TTS synthesis has been performed yet")
        return self._last_metrics
