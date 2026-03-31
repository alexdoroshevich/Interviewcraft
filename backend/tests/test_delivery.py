"""Smoke tests for the voice delivery analyzer."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.delivery.analyzer import (
    _analyze_from_turns,
    _analyze_from_word_timestamps,
    _count_fillers,
    _empty_analysis,
    _score_delivery,
    analyze_delivery,
)

# ── Filler detection ───────────────────────────────────────────────────────────


def test_count_fillers_detects_um_uh() -> None:
    by_type, total = _count_fillers("um I was thinking uh about the design")
    assert by_type.get("um_uh", 0) == 2
    assert total == 2


def test_count_fillers_detects_you_know() -> None:
    by_type, total = _count_fillers("you know it was like really hard")
    assert by_type.get("you_know", 0) == 1
    assert by_type.get("like", 0) == 1
    assert total == 2


def test_count_fillers_empty_text() -> None:
    by_type, total = _count_fillers("")
    assert total == 0
    assert by_type == {}


def test_count_fillers_clean_text() -> None:
    by_type, total = _count_fillers("I implemented a caching layer using Redis")
    assert total == 0


# ── Delivery scoring ───────────────────────────────────────────────────────────


def test_score_delivery_clean() -> None:
    score, tips = _score_delivery(
        filler_rate=0.01,
        wpm=145,
        long_pause_count=0,
        has_word_timestamps=True,
    )
    assert score == 100
    assert any("Strong" in t for t in tips)


def test_score_delivery_high_fillers() -> None:
    score, tips = _score_delivery(
        filler_rate=0.12,
        wpm=145,
        long_pause_count=0,
        has_word_timestamps=True,
    )
    assert score <= 75
    assert any("filler" in t.lower() for t in tips)


def test_score_delivery_slow_pace() -> None:
    score, tips = _score_delivery(
        filler_rate=0.01,
        wpm=80,
        long_pause_count=0,
        has_word_timestamps=True,
    )
    assert score < 100
    assert any("slow" in t.lower() or "pace" in t.lower() for t in tips)


def test_score_delivery_never_goes_negative() -> None:
    score, _ = _score_delivery(
        filler_rate=0.5,
        wpm=50,
        long_pause_count=20,
        has_word_timestamps=True,
    )
    assert score >= 0


# ── Turn-level fallback ────────────────────────────────────────────────────────


def test_analyze_from_turns_basic() -> None:
    transcript = [
        {"role": "assistant", "content": "Tell me about yourself", "ts_ms": 0},
        {
            "role": "user",
            "content": "I am a software engineer with five years of experience",
            "ts_ms": 5000,
        },
        {
            "role": "user",
            "content": "I worked on um distributed systems and uh microservices",
            "ts_ms": 10000,
        },
    ]
    result = _analyze_from_turns(transcript)
    assert result.total_words > 0
    assert result.filler_count == 2
    assert result.wpm > 0
    assert not result.has_word_timestamps


def test_analyze_from_turns_empty() -> None:
    result = _analyze_from_turns([])
    assert result.total_words == 0
    assert result.delivery_grade == "No data"


# ── Empty analysis ─────────────────────────────────────────────────────────────


def test_empty_analysis() -> None:
    result = _empty_analysis(has_word_timestamps=False)
    assert result.delivery_score == 0
    assert result.total_words == 0


# ── Moderate filler rate (0.05–0.10) ─────────────────────────────────────────


def test_score_delivery_moderate_fillers() -> None:
    score, tips = _score_delivery(
        filler_rate=0.07,
        wpm=145,
        long_pause_count=0,
        has_word_timestamps=True,
    )
    assert score == 88  # 100 - 12
    assert any("filler" in t.lower() or "replacing" in t.lower() for t in tips)


def test_score_delivery_minor_fillers() -> None:
    score, tips = _score_delivery(
        filler_rate=0.03,
        wpm=145,
        long_pause_count=0,
        has_word_timestamps=True,
    )
    assert score == 96  # 100 - 4
    assert any("minor" in t.lower() for t in tips)


def test_score_delivery_fast_pace() -> None:
    score, tips = _score_delivery(
        filler_rate=0.01,
        wpm=200,
        long_pause_count=0,
        has_word_timestamps=True,
    )
    assert score == 92  # 100 - 8
    assert any("fast" in t.lower() or "slow down" in t.lower() for t in tips)


def test_score_delivery_few_long_pauses_with_timestamps() -> None:
    """1-3 long pauses → tip but no score deduction."""
    score, tips = _score_delivery(
        filler_rate=0.01,
        wpm=145,
        long_pause_count=2,
        has_word_timestamps=True,
    )
    assert score == 100  # no score deduction for <=3 pauses
    assert any("pause" in t.lower() for t in tips)


def test_score_delivery_many_pauses_no_timestamps_no_penalty() -> None:
    """Long pause penalty only applies when has_word_timestamps=True."""
    score, tips = _score_delivery(
        filler_rate=0.01,
        wpm=145,
        long_pause_count=10,
        has_word_timestamps=False,
    )
    assert score == 100  # no pause penalty without word timestamps


# ── Word-timestamp analysis ───────────────────────────────────────────────────


def _make_word(word: str, start_ms: int, end_ms: int) -> MagicMock:
    w = MagicMock()
    w.word = word
    w.start_ms = start_ms
    w.end_ms = end_ms
    return w


def test_analyze_from_word_timestamps_basic() -> None:
    """Word-level analysis computes WPM and detects fillers."""
    words = [
        _make_word("um", 0, 200),
        _make_word("I", 300, 450),
        _make_word("worked", 500, 700),
        _make_word("on", 750, 850),
        _make_word("Redis", 900, 1200),
    ]
    result = _analyze_from_word_timestamps(words)

    assert result.total_words == 5
    assert result.filler_count == 1  # "um"
    assert result.has_word_timestamps is True
    assert result.wpm > 0


def test_analyze_from_word_timestamps_detects_hesitation_gap() -> None:
    """Gap >= 1500ms between consecutive words detected as hesitation."""
    words = [
        _make_word("I", 0, 200),
        _make_word("was", 2000, 2200),  # 1800ms gap — over threshold
    ]
    result = _analyze_from_word_timestamps(words)
    assert len(result.hesitation_gaps) == 1
    assert result.hesitation_gaps[0]["duration_ms"] == 1800


def test_analyze_from_word_timestamps_empty_returns_zero() -> None:
    """Empty word list → zero-value result."""
    result = _analyze_from_word_timestamps([])
    assert result.total_words == 0
    assert result.delivery_score == 0


# ── analyze_delivery (async, DB path) ────────────────────────────────────────


@pytest.mark.asyncio
async def test_analyze_delivery_uses_word_timestamps_when_available() -> None:
    """analyze_delivery uses word-level timestamps if DB returns words."""
    words = [
        _make_word("Hello", 0, 300),
        _make_word("world", 400, 700),
    ]
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = words
    db.execute = AsyncMock(return_value=mock_result)

    result = await analyze_delivery(
        session_id=uuid.uuid4(),
        transcript=[],
        db=db,
    )
    assert result.has_word_timestamps is True


@pytest.mark.asyncio
async def test_analyze_delivery_falls_back_to_turns_when_no_words() -> None:
    """analyze_delivery falls back to turn-level when no transcript_words."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    transcript = [
        {"role": "user", "content": "I built a caching layer", "ts_ms": 1000},
    ]
    result = await analyze_delivery(
        session_id=uuid.uuid4(),
        transcript=transcript,
        db=db,
    )
    assert result.has_word_timestamps is False


# ── Turn-level: with timestamp gaps ──────────────────────────────────────────


def test_analyze_from_turns_detects_long_inter_turn_gap() -> None:
    """Inter-turn gap >= 10s is detected as a hesitation."""
    transcript = [
        {"role": "user", "content": "I started", "ts_ms": 0},
        {"role": "user", "content": "and then continued", "ts_ms": 15000},  # 15s gap
    ]
    result = _analyze_from_turns(transcript)
    assert len(result.hesitation_gaps) == 1
    assert result.hesitation_gaps[0]["duration_ms"] == 15000
