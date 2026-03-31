"""Shared data types for the voice pipeline.

These are plain dataclasses — no SQLAlchemy or Pydantic dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass
class WordTimestamp:
    """Single word with Deepgram Nova-2 word-level timestamps."""

    word: str
    start_ms: int
    end_ms: int
    confidence: float
    speaker: str | None = None


@dataclass
class TranscriptChunk:
    """One STT result — either a partial or a final transcript segment."""

    text: str
    is_final: bool
    words: list[WordTimestamp] = field(default_factory=list)
    confidence: float = 1.0
    start_ms: int = 0
    end_ms: int = 0


@dataclass
class LLMMetrics:
    """Usage metrics captured after an LLM generation completes."""

    ttft_ms: int  # Time to first token (ms)
    total_latency_ms: int  # Full generation time (ms)
    input_tokens: int
    output_tokens: int
    cached_tokens: int = 0  # Anthropic cache_read_input_tokens


@dataclass
class TTSMetrics:
    """Usage metrics captured after a TTS synthesis completes."""

    first_byte_ms: int  # Time from request to first audio byte (ms)
    total_latency_ms: int
    characters: int


class PipelineState(StrEnum):
    """State machine for the voice pipeline turn."""

    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"  # STT final → LLM generating
    SPEAKING = "speaking"  # TTS audio playing on client
    SOFT_PROMPT = "soft_prompt"  # "take your time..."


@dataclass
class LatencySnapshot:
    """End-to-end latency for one voice exchange — stored in session_metrics."""

    stt_latency_ms: int | None = None
    llm_ttft_ms: int | None = None
    tts_latency_ms: int | None = None
    e2e_latency_ms: int | None = None
