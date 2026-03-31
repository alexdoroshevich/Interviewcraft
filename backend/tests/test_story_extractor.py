"""Unit tests for StoryExtractor service."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.memory.story_extractor import StoryExtractor, _build_extraction_prompt

# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_db(existing_story: Any = None) -> AsyncMock:
    """Mock DB session. existing_story=None means no story found."""
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_story
    db.execute = AsyncMock(return_value=result)
    return db


def _make_transcript(n: int = 4) -> list[dict[str, Any]]:
    turns = []
    for i in range(n):
        role = "assistant" if i % 2 == 0 else "user"
        turns.append({"role": role, "content": f"Turn {i} content", "ts_ms": i * 1000})
    return turns


def _make_anthropic_response(story_detected: bool = True) -> MagicMock:
    """Build a mock Anthropic response with a tool_use block."""
    data: dict[str, Any] = {
        "story_detected": story_detected,
        "title": "Database Migration at Startup X" if story_detected else None,
        "summary": "Led migration for 500M records" if story_detected else None,
        "competencies": ["technical_leadership", "execution"] if story_detected else [],
        "overuse_warning": None,
    }
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "extract_story"
    tool_block.input = data

    mock_usage = MagicMock()
    mock_usage.input_tokens = 50
    mock_usage.output_tokens = 80

    response = MagicMock()
    response.content = [tool_block]
    response.usage = mock_usage
    return response


# ── Empty transcript ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_story_empty_transcript_returns_none() -> None:
    """Empty transcript → None without any LLM call."""
    db = _make_db()
    extractor = StoryExtractor(api_key="key")

    with patch.object(extractor, "_call_anthropic", new=AsyncMock()) as mock_call:
        result = await extractor.extract_story_proposal(
            db=db,
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=[],
        )

    assert result is None
    mock_call.assert_not_called()


# ── Already extracted ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_story_already_saved_returns_none() -> None:
    """Story already saved from this session → None (no duplicate)."""
    existing = MagicMock()  # non-None means story exists
    db = _make_db(existing_story=existing)
    extractor = StoryExtractor(api_key="key")

    with patch.object(extractor, "_call_anthropic", new=AsyncMock()) as mock_call:
        result = await extractor.extract_story_proposal(
            db=db,
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=_make_transcript(),
        )

    assert result is None
    mock_call.assert_not_called()


# ── Story detected ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_story_detected_returns_proposal() -> None:
    """Story detected by LLM → proposal dict returned."""
    db = _make_db(existing_story=None)
    session_id = uuid.uuid4()
    user_id = uuid.uuid4()
    extractor = StoryExtractor(api_key="key")

    llm_result = {
        "story_detected": True,
        "title": "Database Migration at Startup X",
        "summary": "Led migration for 500M records",
        "competencies": ["technical_leadership", "execution"],
        "overuse_warning": None,
    }

    with patch.object(extractor, "_call_anthropic", new=AsyncMock(return_value=llm_result)):
        result = await extractor.extract_story_proposal(
            db=db,
            user_id=user_id,
            session_id=session_id,
            transcript=_make_transcript(),
        )

    assert result is not None
    assert result["proposed_title"] == "Database Migration at Startup X"
    assert result["proposed_summary"] == "Led migration for 500M records"
    assert "technical_leadership" in result["proposed_competencies"]
    assert result["already_saved"] is False
    assert result["session_id"] == str(session_id)


# ── Story not detected ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_story_not_detected_returns_none() -> None:
    """LLM says story_detected=False → None."""
    db = _make_db(existing_story=None)
    extractor = StoryExtractor(api_key="key")

    llm_result = {
        "story_detected": False,
        "title": None,
        "summary": None,
        "competencies": [],
    }

    with patch.object(extractor, "_call_anthropic", new=AsyncMock(return_value=llm_result)):
        result = await extractor.extract_story_proposal(
            db=db,
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=_make_transcript(),
        )

    assert result is None


# ── LLM exception → graceful None ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_story_llm_exception_returns_none() -> None:
    """Any LLM exception → logged and None returned (not raised)."""
    db = _make_db(existing_story=None)
    extractor = StoryExtractor(api_key="key")

    with patch.object(
        extractor,
        "_call_anthropic",
        new=AsyncMock(side_effect=RuntimeError("API error")),
    ):
        result = await extractor.extract_story_proposal(
            db=db,
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=_make_transcript(),
        )

    assert result is None


# ── Invalid competencies filtered ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_extract_story_invalid_competencies_filtered_out() -> None:
    """Competencies not in the known list are silently dropped."""
    db = _make_db(existing_story=None)
    extractor = StoryExtractor(api_key="key")

    llm_result = {
        "story_detected": True,
        "title": "My Story",
        "summary": "A great achievement",
        "competencies": ["technical_leadership", "unknown_competency_xyz", "execution"],
    }

    with patch.object(extractor, "_call_anthropic", new=AsyncMock(return_value=llm_result)):
        result = await extractor.extract_story_proposal(
            db=db,
            user_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            transcript=_make_transcript(),
        )

    assert result is not None
    assert "unknown_competency_xyz" not in result["proposed_competencies"]
    assert "technical_leadership" in result["proposed_competencies"]


# ── _call_anthropic: no tool_use block → ValueError ──────────────────────────


@pytest.mark.asyncio
async def test_call_anthropic_no_tool_block_raises() -> None:
    """_call_anthropic raises ValueError when no tool_use block returned."""
    text_block = MagicMock()
    text_block.type = "text"

    mock_usage = MagicMock()
    mock_usage.input_tokens = 10
    mock_usage.output_tokens = 5

    mock_response = MagicMock()
    mock_response.content = [text_block]
    mock_response.usage = mock_usage

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    db = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.memory.story_extractor.AsyncAnthropic", return_value=mock_client):
        extractor = StoryExtractor(api_key="key")
        with pytest.raises(ValueError, match="No tool_use block"):
            await extractor._call_anthropic(
                prompt="test prompt",
                session_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                db=db,
            )


# ── _build_extraction_prompt ──────────────────────────────────────────────────


def test_build_extraction_prompt_contains_transcript() -> None:
    """Prompt includes formatted transcript turns."""
    transcript = [
        {"role": "assistant", "content": "Tell me about a challenge"},
        {"role": "user", "content": "I led a database migration"},
    ]
    prompt = _build_extraction_prompt(transcript, story_hint=None)

    assert "INTERVIEWER" in prompt
    assert "CANDIDATE" in prompt
    assert "database migration" in prompt


def test_build_extraction_prompt_with_hint() -> None:
    """story_hint is included in the prompt."""
    transcript = [{"role": "user", "content": "some content"}]
    prompt = _build_extraction_prompt(transcript, story_hint="The Migration Story")

    assert "The Migration Story" in prompt


def test_build_extraction_prompt_no_hint_omits_note() -> None:
    """No story_hint → hint note is absent."""
    transcript = [{"role": "user", "content": "content"}]
    prompt = _build_extraction_prompt(transcript, story_hint=None)

    assert "Note: A story titled" not in prompt


def test_build_extraction_prompt_caps_at_30_turns() -> None:
    """Prompt only includes first 30 transcript turns regardless of length."""
    transcript = [{"role": "user", "content": f"turn {i}"} for i in range(50)]
    prompt = _build_extraction_prompt(transcript, story_hint=None)

    # turn 30 and beyond should not appear
    assert "turn 29" in prompt
    assert "turn 30" not in prompt
