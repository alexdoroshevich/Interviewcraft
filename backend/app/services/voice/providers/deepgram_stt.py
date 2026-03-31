"""Deepgram Nova-2 STT provider — streaming WebSocket with word-level timestamps.

CRITICAL (spec): Word-level timestamps MUST be captured here.
They are persisted to transcript_words table (TTL 14d) by the pipeline, NOT stored in session JSONB.

Audio format expected from browser: webm/opus (MediaRecorder default).
Deepgram also accepts: linear16, flac, mp3, opus, ogg/opus.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import structlog
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents

from app.services.voice.interfaces import STTProvider
from app.services.voice.types import TranscriptChunk, WordTimestamp

logger = structlog.get_logger(__name__)

# Deepgram Nova-2 streaming configuration
_LIVE_OPTIONS = LiveOptions(
    model="nova-2",
    language="en-US",
    # No encoding — Deepgram auto-detects webm/opus from browser MediaRecorder
    channels=1,
    punctuate=True,
    smart_format=True,
    interim_results=True,  # Partials for smart pause detection
    # Word-level timestamps are returned by default in response alternatives
    utterance_end_ms="1000",  # Signal utterance end after 1.0s silence (was 1500ms)
    vad_events=True,
    endpointing=300,  # Wait 300ms of audio silence before finalizing (was 500ms)
)


class DeepgramSTTProvider(STTProvider):
    """Deepgram Nova-2 streaming STT.

    Bridges Deepgram's callback API to an AsyncGenerator using asyncio.Queue.
    Confidence < 0.60 → partial treated as unreliable (pipeline handles retry prompt).
    """

    STT_CONFIDENCE_THRESHOLD = 0.60

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def transcribe_stream(  # type: ignore[override]
        self,
        audio_chunks: AsyncGenerator[bytes],
    ) -> AsyncGenerator[TranscriptChunk]:
        queue: asyncio.Queue[TranscriptChunk | None] = asyncio.Queue()
        connection = DeepgramClient(self._api_key).listen.asynclive.v("1")

        # ── Callbacks ──────────────────────────────────────────────────────────
        async def _on_transcript(_self: object, result: object, **_: object) -> None:
            try:
                channel = result.channel  # type: ignore[attr-defined]
                alt = channel.alternatives[0]
                if not alt.transcript:
                    return

                words = [
                    WordTimestamp(
                        word=w.word,
                        start_ms=int(w.start * 1000),
                        end_ms=int(w.end * 1000),
                        confidence=w.confidence,
                        speaker=getattr(w, "speaker", None),
                    )
                    for w in (alt.words or [])
                ]

                chunk = TranscriptChunk(
                    text=alt.transcript,
                    is_final=result.is_final,  # type: ignore[attr-defined]
                    words=words,
                    confidence=alt.confidence,
                    start_ms=words[0].start_ms if words else 0,
                    end_ms=words[-1].end_ms if words else 0,
                )
                await queue.put(chunk)
            except Exception as exc:
                logger.error("deepgram_stt.transcript_callback_error", error=str(exc))

        async def _on_error(_self: object, error: object, **_: object) -> None:
            logger.error("deepgram_stt.error", error=str(error))
            await queue.put(None)

        async def _on_close(_self: object, close: object, **_: object) -> None:
            logger.debug("deepgram_stt.connection_closed")
            await queue.put(None)

        connection.on(LiveTranscriptionEvents.Transcript, _on_transcript)
        connection.on(LiveTranscriptionEvents.Error, _on_error)
        connection.on(LiveTranscriptionEvents.Close, _on_close)

        # ── Start connection ───────────────────────────────────────────────────
        started = await connection.start(_LIVE_OPTIONS)
        if not started:
            raise RuntimeError("Failed to connect to Deepgram Nova-2 — check API key and network")

        logger.info("deepgram_stt.connected")

        # ── Send audio + keepalive in background ─────────────────────────────
        async def _send_audio() -> None:
            try:
                async for chunk in audio_chunks:
                    await connection.send(chunk)
            except Exception as exc:
                logger.error("deepgram_stt.send_error", error=str(exc))
            finally:
                await connection.finish()

        async def _keepalive() -> None:
            """Send KeepAlive every 5s to prevent Deepgram timeout during bot speaking."""
            try:
                while True:
                    await asyncio.sleep(5)
                    try:
                        await connection.keep_alive()
                    except Exception:
                        break
            except asyncio.CancelledError:
                pass

        send_task = asyncio.create_task(_send_audio())
        keepalive_task = asyncio.create_task(_keepalive())

        # ── Yield results from queue ───────────────────────────────────────────
        try:
            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            keepalive_task.cancel()
            send_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass
            try:
                await send_task
            except asyncio.CancelledError:
                pass
            logger.info("deepgram_stt.stream_ended")
