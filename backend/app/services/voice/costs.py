"""Provider pricing and cost calculation.

Prices verified February 2026 (from HANDOFF.md).
Log every cost to usage_logs — UI displays cost per session (DoD item 5).
"""

from decimal import Decimal

# ── Anthropic ──────────────────────────────────────────────────────────────────
# Per million tokens (input / output)
ANTHROPIC_PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 1.0, "output": 5.0},
    # Legacy dated alias — kept so existing usage_logs rows still resolve
    "claude-haiku-4-5-20251001": {"input": 1.0, "output": 5.0},
}
# Cached input tokens are billed at 10% of the normal input price
ANTHROPIC_CACHE_DISCOUNT = 0.10

# ── Deepgram ───────────────────────────────────────────────────────────────────
DEEPGRAM_STT_PER_MINUTE = 0.0058  # Nova-2
DEEPGRAM_TTS_PER_1K_CHARS = 0.015  # Aura-1

# ── ElevenLabs ─────────────────────────────────────────────────────────────────
ELEVENLABS_PER_1K_CHARS = 0.06  # Turbo v2.5


def calc_anthropic_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> Decimal:
    """Return total cost in USD for one Anthropic API call."""
    if model not in ANTHROPIC_PRICES:
        raise ValueError(f"Unknown Anthropic model: {model}")
    rates = ANTHROPIC_PRICES[model]
    non_cached = input_tokens - cached_tokens
    cost = (
        (non_cached / 1_000_000) * rates["input"]
        + (cached_tokens / 1_000_000) * rates["input"] * ANTHROPIC_CACHE_DISCOUNT
        + (output_tokens / 1_000_000) * rates["output"]
    )
    return Decimal(str(round(cost, 6)))


def calc_deepgram_stt_cost(audio_seconds: float) -> Decimal:
    """Return cost in USD for Deepgram Nova-2 STT."""
    minutes = audio_seconds / 60.0
    return Decimal(str(round(minutes * DEEPGRAM_STT_PER_MINUTE, 6)))


def calc_deepgram_tts_cost(characters: int) -> Decimal:
    """Return cost in USD for Deepgram Aura-1 TTS."""
    return Decimal(str(round((characters / 1000) * DEEPGRAM_TTS_PER_1K_CHARS, 6)))


def calc_elevenlabs_cost(characters: int) -> Decimal:
    """Return cost in USD for ElevenLabs Turbo v2.5."""
    return Decimal(str(round((characters / 1000) * ELEVENLABS_PER_1K_CHARS, 6)))
