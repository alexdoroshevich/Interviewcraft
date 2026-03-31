"""Unit tests for MemoryExtractor service.

Covers:
- Empty transcript returns defaults without calling Anthropic
- Full extraction with mocked Anthropic response updates skills
- Missing tool_use block falls back gracefully
- Prompt builder contains expected keywords
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.memory.memory_extractor import MemoryExtractor, _build_extraction_prompt

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_mock_db() -> AsyncMock:
    """Return a minimal AsyncSession mock."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = MagicMock()
    return db


def _make_anthropic_response(tool_input: dict) -> MagicMock:
    """Build a mock Anthropic response containing a tool_use block."""
    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.name = "extract_memory"
    mock_block.input = tool_input

    mock_response = MagicMock()
    mock_response.usage.input_tokens = 150
    mock_response.usage.output_tokens = 80
    mock_response.content = [mock_block]
    return mock_response


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_empty_transcript_returns_defaults() -> None:
    """Empty transcript / segment_scores should short-circuit without any LLM call."""
    mock_anthropic_client = AsyncMock()

    with patch(
        "app.services.memory.memory_extractor.AsyncAnthropic",
        return_value=mock_anthropic_client,
    ):
        extractor = MemoryExtractor(api_key="test-key")
        result = await extractor.extract_and_update(
            db=_make_mock_db(),
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=[],
            segment_scores=[],
        )

    assert result["skill_signals"] == []
    assert result["story_detected"] is False
    assert result["story_title"] is None
    assert result["communication_notes"] is None
    assert result["updated_skills"] == []
    mock_anthropic_client.messages.create.assert_not_called()


@pytest.mark.asyncio
async def test_extract_with_data_calls_anthropic_and_updates_skills() -> None:
    """Full extraction returns parsed tool output and updates the skill graph."""
    tool_input = {
        "skill_signals": [
            {"skill": "star_structure", "direction": "positive", "note": "Good structure"}
        ],
        "story_detected": True,
        "story_title": "Led team migration",
        "communication_notes": "Clear and concise",
    }
    mock_response = _make_anthropic_response(tool_input)

    mock_anthropic_client = AsyncMock()
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    with (
        patch(
            "app.services.memory.memory_extractor.AsyncAnthropic",
            return_value=mock_anthropic_client,
        ),
        patch(
            "app.services.memory.memory_extractor.log_usage",
            new=AsyncMock(),
        ),
        patch(
            "app.services.memory.memory_extractor.skill_graph_service.update_from_scoring_result",
            new=AsyncMock(return_value=[]),
        ),
    ):
        extractor = MemoryExtractor(api_key="test-key")
        result = await extractor.extract_and_update(
            db=_make_mock_db(),
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=[{"role": "user", "content": "I led a team migration...", "ts_ms": 0}],
            segment_scores=[{"segment_index": 0, "overall_score": 75, "rules_triggered": []}],
        )

    assert result["story_detected"] is True
    assert result["story_title"] == "Led team migration"
    assert result["skill_signals"][0]["skill"] == "star_structure"
    mock_anthropic_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_extract_no_tool_use_block_returns_empty() -> None:
    """When Anthropic returns no tool_use block, extraction fails gracefully."""
    # Response with a non-tool_use block only
    text_block = MagicMock()
    text_block.type = "text"

    mock_response = MagicMock()
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 20
    mock_response.content = [text_block]

    mock_anthropic_client = AsyncMock()
    mock_anthropic_client.messages.create = AsyncMock(return_value=mock_response)

    with (
        patch(
            "app.services.memory.memory_extractor.AsyncAnthropic",
            return_value=mock_anthropic_client,
        ),
        patch(
            "app.services.memory.memory_extractor.log_usage",
            new=AsyncMock(),
        ),
    ):
        extractor = MemoryExtractor(api_key="test-key")
        result = await extractor.extract_and_update(
            db=_make_mock_db(),
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=[{"role": "user", "content": "Some answer", "ts_ms": 0}],
            segment_scores=[{"segment_index": 0, "overall_score": 60, "rules_triggered": []}],
        )

    assert result["updated_skills"] == []
    assert result["story_detected"] is False
    assert result["skill_signals"] == []


def test_build_extraction_prompt_contains_transcript() -> None:
    """Prompt includes the word CANDIDATE and the transcript content."""
    prompt = _build_extraction_prompt(
        transcript=[{"role": "user", "content": "Hello", "ts_ms": 0}],
        segment_scores=[{"segment_index": 0, "overall_score": 70}],
    )

    assert isinstance(prompt, str)
    assert "CANDIDATE" in prompt
    assert "Hello" in prompt
