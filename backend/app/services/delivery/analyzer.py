"""Voice delivery analyzer — pure Python, no LLM required.

Computes:
- Filler words (um, uh, like, you know, basically, ...)
- Words per minute (WPM)
- Hesitation gaps > GAP_THRESHOLD_MS between consecutive user words
- Delivery score (0–100) based on filler rate, WPM, and gap count

Data sources (priority order):
1. transcript_words table — word-level timestamps from Deepgram (14d TTL)
2. transcript JSONB turns — fallback when transcript_words have expired
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript_word import TranscriptWord

logger = structlog.get_logger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

# Filler words to detect (matched as whole words, case-insensitive)
_FILLERS: dict[str, list[str]] = {
    "um_uh": ["um", "uh", "uhh", "umm"],
    "like": ["like"],
    "you_know": ["you know"],
    "basically": ["basically"],
    "literally": ["literally"],
    "so": ["so"],
    "actually": ["actually"],
    "right": ["right"],
    "kind_of": ["kind of", "kinda"],
    "sort_of": ["sort of", "sorta"],
}

# Gap between consecutive words that counts as a hesitation pause (ms)
_GAP_THRESHOLD_MS = 1500

# Ideal speaking pace range (WPM)
_WPM_LOW = 110
_WPM_HIGH = 180


# ── Output types ──────────────────────────────────────────────────────────────


@dataclass
class HesitationGap:
    """A detected pause in the user's speech."""

    start_ms: int
    end_ms: int
    duration_ms: int


@dataclass
class DeliveryAnalysis:
    """Full delivery analysis for a session."""

    # Raw counts
    total_words: int
    duration_seconds: float
    wpm: float

    # Fillers
    filler_count: int
    filler_rate: float  # fillers / total_words (0.0–1.0)
    fillers_by_type: dict[str, int]
    top_filler: str | None  # most frequent filler category

    # Hesitation gaps
    hesitation_gaps: list[dict]  # serialisable form of HesitationGap
    long_pause_count: int  # gaps ≥ 3 s
    has_word_timestamps: bool  # False when falling back to turn-level analysis

    # Score
    delivery_score: int  # 0–100
    delivery_grade: str  # "Excellent" / "Good" / "Fair" / "Needs Work"
    coaching_tips: list[str]


# ── Analyzer ──────────────────────────────────────────────────────────────────


async def analyze_delivery(
    session_id: uuid.UUID,
    transcript: list[dict],
    db: AsyncSession,
) -> DeliveryAnalysis:
    """Compute delivery metrics for a session.

    Tries word-level timestamps first; falls back to turn-level analysis.
    """
    words = await _fetch_transcript_words(db, session_id)

    if words:
        return _analyze_from_word_timestamps(words)
    else:
        logger.info(
            "delivery.fallback_to_turns",
            session_id=str(session_id),
            reason="transcript_words expired or empty",
        )
        return _analyze_from_turns(transcript)


# ── Word-timestamp path ────────────────────────────────────────────────────────


async def _fetch_transcript_words(
    db: AsyncSession,
    session_id: uuid.UUID,
) -> list[TranscriptWord]:
    """Load user-speaker words ordered by start_ms."""
    result = await db.execute(
        select(TranscriptWord)
        .where(TranscriptWord.session_id == session_id)
        .order_by(TranscriptWord.start_ms)
    )
    return list(result.scalars().all())


def _analyze_from_word_timestamps(words: list[TranscriptWord]) -> DeliveryAnalysis:
    """Full analysis using word-level timestamps."""
    if not words:
        return _empty_analysis(has_word_timestamps=True)

    # Build plain-text corpus
    text = " ".join(w.word for w in words)
    total_words = len(words)

    # Duration from first word start to last word end
    duration_ms = max(w.end_ms for w in words) - min(w.start_ms for w in words)
    duration_seconds = max(duration_ms / 1000, 1.0)
    wpm = round((total_words / duration_seconds) * 60, 1)

    # Filler counts
    fillers_by_type, filler_count = _count_fillers(text)

    # Hesitation gaps
    gaps: list[HesitationGap] = []
    for i in range(1, len(words)):
        gap_ms = words[i].start_ms - words[i - 1].end_ms
        if gap_ms >= _GAP_THRESHOLD_MS:
            gaps.append(
                HesitationGap(
                    start_ms=words[i - 1].end_ms,
                    end_ms=words[i].start_ms,
                    duration_ms=gap_ms,
                )
            )

    return _build_result(
        total_words=total_words,
        duration_seconds=duration_seconds,
        wpm=wpm,
        filler_count=filler_count,
        fillers_by_type=fillers_by_type,
        gaps=gaps,
        has_word_timestamps=True,
    )


# ── Turn-level fallback path ───────────────────────────────────────────────────


def _analyze_from_turns(transcript: list[dict]) -> DeliveryAnalysis:
    """Fallback analysis using only transcript turn text + timestamps."""
    user_turns = [t for t in transcript if t.get("role") == "user" and t.get("content")]
    if not user_turns:
        return _empty_analysis(has_word_timestamps=False)

    full_text = " ".join(t["content"] for t in user_turns)
    total_words = len(full_text.split())

    # Estimate duration from first/last ts_ms
    timestamps = [t["ts_ms"] for t in user_turns if t.get("ts_ms") is not None]
    if len(timestamps) >= 2:
        # Add ~5s for last turn speaking time (rough estimate)
        duration_seconds = max((max(timestamps) - min(timestamps)) / 1000 + 5.0, 1.0)
    else:
        duration_seconds = max(total_words / 2.5, 1.0)  # assume ~150 WPM fallback

    wpm = round((total_words / duration_seconds) * 60, 1)
    fillers_by_type, filler_count = _count_fillers(full_text)

    # Without word timestamps we can detect inter-turn gaps (> 10s = notable pause)
    gaps: list[HesitationGap] = []
    for i in range(1, len(user_turns)):
        ts_curr = user_turns[i].get("ts_ms")
        ts_prev = user_turns[i - 1].get("ts_ms")
        if ts_curr is not None and ts_prev is not None:
            gap_ms = ts_curr - ts_prev
            if gap_ms >= 10_000:  # turns with > 10 s gap
                gaps.append(
                    HesitationGap(
                        start_ms=ts_prev,
                        end_ms=ts_curr,
                        duration_ms=gap_ms,
                    )
                )

    return _build_result(
        total_words=total_words,
        duration_seconds=duration_seconds,
        wpm=wpm,
        filler_count=filler_count,
        fillers_by_type=fillers_by_type,
        gaps=gaps,
        has_word_timestamps=False,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────


def _count_fillers(text: str) -> tuple[dict[str, int], int]:
    """Count filler words in text. Returns (by_type_dict, total_count)."""
    text_lower = text.lower()
    by_type: dict[str, int] = {}

    for category, patterns in _FILLERS.items():
        count = 0
        for pattern in patterns:
            # Whole-word match
            count += len(re.findall(rf"\b{re.escape(pattern)}\b", text_lower))
        if count > 0:
            by_type[category] = count

    total = sum(by_type.values())
    return by_type, total


def _build_result(
    *,
    total_words: int,
    duration_seconds: float,
    wpm: float,
    filler_count: int,
    fillers_by_type: dict[str, int],
    gaps: list[HesitationGap],
    has_word_timestamps: bool,
) -> DeliveryAnalysis:
    filler_rate = filler_count / max(total_words, 1)
    long_pause_count = sum(1 for g in gaps if g.duration_ms >= 3000)
    top_filler = max(fillers_by_type, key=lambda k: fillers_by_type[k]) if fillers_by_type else None

    score, tips = _score_delivery(
        filler_rate=filler_rate,
        wpm=wpm,
        long_pause_count=long_pause_count,
        has_word_timestamps=has_word_timestamps,
    )

    grade = (
        "Excellent"
        if score >= 90
        else "Good"
        if score >= 75
        else "Fair"
        if score >= 60
        else "Needs Work"
    )

    return DeliveryAnalysis(
        total_words=total_words,
        duration_seconds=round(duration_seconds, 1),
        wpm=wpm,
        filler_count=filler_count,
        filler_rate=round(filler_rate, 4),
        fillers_by_type=fillers_by_type,
        top_filler=top_filler,
        hesitation_gaps=[
            {"start_ms": g.start_ms, "end_ms": g.end_ms, "duration_ms": g.duration_ms} for g in gaps
        ],
        long_pause_count=long_pause_count,
        has_word_timestamps=has_word_timestamps,
        delivery_score=score,
        delivery_grade=grade,
        coaching_tips=tips,
    )


def _score_delivery(
    *,
    filler_rate: float,
    wpm: float,
    long_pause_count: int,
    has_word_timestamps: bool,
) -> tuple[int, list[str]]:
    """Compute delivery score (0-100) and actionable tips."""
    score = 100
    tips: list[str] = []

    # Filler penalty
    if filler_rate > 0.10:
        score -= 25
        tips.append(
            "High filler word rate — practice pausing silently instead of using 'um', 'uh', or 'like'."
        )
    elif filler_rate > 0.05:
        score -= 12
        tips.append(
            "Some filler words detected — try replacing them with a brief pause to sound more confident."
        )
    elif filler_rate > 0.02:
        score -= 4
        tips.append("Minor filler word usage — generally not distracting but worth reducing.")

    # Pace penalty
    if wpm < _WPM_LOW:
        score -= 10
        tips.append(
            f"Speaking pace is slow ({wpm:.0f} WPM) — aim for {_WPM_LOW}–{_WPM_HIGH} WPM to keep the interviewer engaged."
        )
    elif wpm > _WPM_HIGH:
        score -= 8
        tips.append(
            f"Speaking pace is fast ({wpm:.0f} WPM) — slow down slightly to improve clarity and give ideas time to land."
        )

    # Long pause penalty (only reliable with word timestamps)
    if has_word_timestamps and long_pause_count > 3:
        score -= min(long_pause_count * 3, 15)
        tips.append(
            f"{long_pause_count} long pauses detected (≥3 s) — structuring your answer beforehand (STAR, REACT) reduces hesitations."
        )
    elif has_word_timestamps and long_pause_count > 0:
        tips.append(
            f"{long_pause_count} notable pause(s) detected — minor hesitations are normal; excessive ones reduce confidence perception."
        )

    if not tips:
        tips.append("Strong delivery — clear pace, minimal fillers, and good flow throughout.")

    return max(score, 0), tips


def _empty_analysis(*, has_word_timestamps: bool) -> DeliveryAnalysis:
    """Return a zero-value analysis when no usable data is available."""
    return DeliveryAnalysis(
        total_words=0,
        duration_seconds=0.0,
        wpm=0.0,
        filler_count=0,
        filler_rate=0.0,
        fillers_by_type={},
        top_filler=None,
        hesitation_gaps=[],
        long_pause_count=0,
        has_word_timestamps=has_word_timestamps,
        delivery_score=0,
        delivery_grade="No data",
        coaching_tips=["No transcript data available to analyze delivery."],
    )
