"""Provider ABCs for the voice pipeline.

CRITICAL (from CLAUDE.md): Provider interfaces are ABCs. Don't bypass them.
ProviderSet has per-task LLMs: voice_llm, scoring_llm, diff_llm, memory_llm.

Implementations live in providers/.  The ProviderFactory selects them based
on the session quality_profile (quality / balanced / budget).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Any

from app.services.voice.types import LLMMetrics, TranscriptChunk, TTSMetrics


class STTProvider(ABC):
    """Streaming speech-to-text.  MUST capture word-level timestamps."""

    @abstractmethod
    def transcribe_stream(
        self,
        audio_chunks: AsyncGenerator[bytes],
    ) -> AsyncGenerator[TranscriptChunk]:
        """Yield TranscriptChunk (partial then final) as audio arrives.

        Word-level timestamps MUST be populated on final chunks.
        These are persisted to transcript_words table (TTL 14d) by the pipeline.
        """
        ...


class LLMProvider(ABC):
    """Language model — both streaming text and structured JSON generation."""

    @abstractmethod
    def generate_stream(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str]:
        """Yield text chunks as they arrive (streaming).

        Call get_last_metrics() after the generator is exhausted.
        """
        ...

    @abstractmethod
    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> tuple[dict[str, Any], LLMMetrics]:
        """Return structured JSON output using tool_use (not raw text).

        Used for single-batched score+diff+memory call (Weeks 3-4).
        Raises ValueError if no valid structured output returned.
        """
        ...

    @abstractmethod
    def get_last_metrics(self) -> LLMMetrics | None:
        """Return metrics from the most recent generate_stream call."""
        ...


class TTSProvider(ABC):
    """Text-to-speech — streaming audio synthesis."""

    @abstractmethod
    def synthesize_stream(
        self,
        text: str,
    ) -> AsyncGenerator[bytes]:
        """Yield PCM audio bytes as they arrive.

        Caller MUST stream first sentence before LLM finishes generating
        (the spec's key latency optimization).
        """
        ...

    @abstractmethod
    async def get_last_metrics(self) -> TTSMetrics:
        """Return metrics from the most recent synthesize_stream call."""
        ...


@dataclass
class ProviderSet:
    """Per-task LLM routing — one field per task type.

    From HANDOFF.md Late Fix #1:
      Quality:  Sonnet for all + ElevenLabs TTS
      Balanced: Sonnet (voice), Haiku (scoring/diff/memory) + ElevenLabs
      Budget:   Haiku all + Deepgram Aura-1 TTS
    """

    stt: STTProvider
    voice_llm: LLMProvider  # Real-time interviewer responses
    scoring_llm: LLMProvider  # Rubric scoring (Weeks 3-4)
    diff_llm: LLMProvider  # Answer diff generation (Weeks 3-4)
    memory_llm: LLMProvider  # Skill graph memory extraction (Weeks 5-6)
    tts: TTSProvider
    quality_profile: str = "balanced"
