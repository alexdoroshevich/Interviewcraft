"""Voice pipeline tuning configuration.

All values are loaded from environment variables at startup.
Set these in your Fly.io secrets (or .env for local dev) to tune the pipeline.
Defaults here are functional but not production-optimised — override via env.

See backend/.env.example for the full list with descriptions.
"""

from __future__ import annotations

import os


def _ms(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


def _s(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


def _f(key: str, default: float) -> float:
    return float(os.getenv(key, str(default)))


def _i(key: str, default: int) -> int:
    return int(os.getenv(key, str(default)))


# ── Smart pause ───────────────────────────────────────────────────────────────
PARTIAL_TIMEOUT_MS: int = _ms("VOICE_PARTIAL_TIMEOUT_MS", 2000)
SOFT_PROMPT_MS: int = _ms("VOICE_SOFT_PROMPT_MS", 10000)
RE_ENGAGE_MS: int = _ms("VOICE_RE_ENGAGE_MS", 18000)

# ── Deepgram STT ──────────────────────────────────────────────────────────────
STT_UTTERANCE_END_MS: str = os.getenv("VOICE_STT_UTTERANCE_END_MS", "1200")
STT_ENDPOINTING_MS: int = _i("VOICE_STT_ENDPOINTING_MS", 400)
STT_CONFIDENCE_THRESHOLD: float = _f("VOICE_STT_CONFIDENCE_THRESHOLD", 0.60)

# ── Pipeline debounce ─────────────────────────────────────────────────────────
PIPELINE_POLL_INTERVAL_S: float = _s("VOICE_POLL_INTERVAL_S", 0.2)
PIPELINE_HARD_CAP_S: float = _s("VOICE_HARD_CAP_S", 30.0)
PIPELINE_COMMIT_SHORT_S: float = _s("VOICE_COMMIT_SHORT_S", 0.5)
PIPELINE_COMMIT_LONG_S: float = _s("VOICE_COMMIT_LONG_S", 1.5)
PIPELINE_COMMIT_THRESHOLD_WORDS: int = _i("VOICE_COMMIT_THRESHOLD_WORDS", 10)
PIPELINE_MIN_WORDS_FOR_LLM: int = _i("VOICE_MIN_WORDS_FOR_LLM", 2)
PIPELINE_CARRYOVER_TIMEOUT_S: float = _s("VOICE_CARRYOVER_TIMEOUT_S", 8.0)
PIPELINE_MAX_WAIT_COUNT: int = _i("VOICE_MAX_WAIT_COUNT", 2)
PIPELINE_LLM_MAX_TOKENS: int = _i("VOICE_LLM_MAX_TOKENS", 256)

# ── ElevenLabs TTS ────────────────────────────────────────────────────────────
TTS_CHUNK_SIZE: int = _i("VOICE_TTS_CHUNK_SIZE", 8192)
TTS_LATENCY_OPT: str = os.getenv("VOICE_TTS_LATENCY_OPT", "3")
TTS_STABILITY: float = _f("VOICE_TTS_STABILITY", 0.5)
TTS_SIMILARITY_BOOST: float = _f("VOICE_TTS_SIMILARITY_BOOST", 0.75)
TTS_STYLE: float = _f("VOICE_TTS_STYLE", 0.0)
