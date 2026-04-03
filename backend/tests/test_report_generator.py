"""Smoke tests for the session report PDF generator.

Covers:
- _format_segments returns expected text for scored segments
- _extract_file_id handles tool_result blocks and direct file_id attributes
- generate_session_pdf raises ValueError for non-completed sessions
- generate_session_pdf returns cached file_id without calling Anthropic
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.report.generator import (
    _extract_file_id,
    _format_segments,
)

# ── _format_segments ─────────────────────────────────────────────────────────


def _make_segment(index: int, score: int, question: str = "Q?") -> MagicMock:
    seg = MagicMock()
    seg.segment_index = index
    seg.overall_score = score
    seg.question_text = question
    seg.category_scores = {"structure": score, "depth": score}
    seg.rules_triggered = [{"rule": "used STAR"}, {"rule": "specific metrics"}]
    seg.diff_versions = None
    return seg


def test_format_segments_basic() -> None:
    segs = [_make_segment(0, 8, "Tell me about yourself")]
    text = _format_segments(segs)
    assert "Q1" in text
    assert "Tell me about yourself" in text
    assert "8/10" in text
    assert "structure" in text


def test_format_segments_empty() -> None:
    assert _format_segments([]) == ""


def test_format_segments_includes_rules() -> None:
    segs = [_make_segment(0, 7)]
    text = _format_segments(segs)
    assert "used STAR" in text


# ── _extract_file_id ─────────────────────────────────────────────────────────


def test_extract_file_id_from_direct_attribute() -> None:
    block = MagicMock()
    block.type = "text"
    block.file_id = "file_abc123"
    block.source = None

    response = MagicMock()
    response.content = [block]
    assert _extract_file_id(response) == "file_abc123"


def test_extract_file_id_from_source_dict() -> None:
    block = MagicMock()
    block.type = "document"
    block.file_id = None
    block.source = {"file_id": "file_xyz789"}

    response = MagicMock()
    response.content = [block]
    assert _extract_file_id(response) == "file_xyz789"


def test_extract_file_id_returns_none_when_absent() -> None:
    block = MagicMock()
    block.type = "text"
    block.file_id = None
    block.source = {}

    response = MagicMock()
    response.content = [block]
    assert _extract_file_id(response) is None


def test_extract_file_id_empty_content() -> None:
    response = MagicMock()
    response.content = []
    assert _extract_file_id(response) is None


# ── generate_session_pdf (error paths, no Anthropic call) ────────────────────


@pytest.mark.asyncio
async def test_generate_raises_for_missing_session() -> None:
    from app.services.report.generator import generate_session_pdf

    db = AsyncMock()
    # scalar_one_or_none returns None → session not found
    db.execute = AsyncMock(return_value=AsyncMock(scalar_one_or_none=MagicMock(return_value=None)))

    with pytest.raises(ValueError, match="Session not found"):
        await generate_session_pdf(
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            api_key="sk-test",
            db=db,
        )


@pytest.mark.asyncio
async def test_generate_raises_for_incomplete_session() -> None:
    from app.services.report.generator import generate_session_pdf

    session = MagicMock()
    session.status = "active"

    db = AsyncMock()
    db.execute = AsyncMock(
        return_value=AsyncMock(scalar_one_or_none=MagicMock(return_value=session))
    )

    with patch("app.redis_client.get_redis", side_effect=Exception("no redis")):
        with pytest.raises(ValueError, match="not completed"):
            await generate_session_pdf(
                session_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                api_key="sk-test",
                db=db,
            )


@pytest.mark.asyncio
async def test_generate_returns_cache_hit_without_db_call() -> None:
    from app.services.report.generator import generate_session_pdf

    session_id = uuid.uuid4()
    cached_file_id = "file_cached_001"

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=cached_file_id)

    db = AsyncMock()

    with patch("app.redis_client.get_redis", return_value=mock_redis):
        result = await generate_session_pdf(
            session_id=session_id,
            user_id=uuid.uuid4(),
            api_key="sk-test",
            db=db,
        )

    assert result == cached_file_id
    db.execute.assert_not_called()
