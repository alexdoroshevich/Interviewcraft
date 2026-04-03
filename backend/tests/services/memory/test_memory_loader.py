"""Unit tests for MemoryLoader.

Covers:
- _format_memory_block: all document sections
- load_memory_context: Redis cache hit, Redis miss + DB None, Redis miss + DB has data
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.memory.loader import _format_memory_block, load_memory_context

# ── _format_memory_block ──────────────────────────────────────────────────────


def _base_doc(**kwargs: object) -> dict:
    return {"total_sessions": 5, **kwargs}


def test_format_empty_doc_returns_empty_string() -> None:
    assert _format_memory_block({}) == ""
    assert _format_memory_block({"total_sessions": 0}) == ""


def test_format_includes_session_count() -> None:
    result = _format_memory_block(_base_doc())
    assert "5 previous sessions" in result


def test_format_career_section() -> None:
    doc = _base_doc(
        target_role="Senior Engineer",
        target_level="L5",
        target_companies=["Google", "Meta"],
        career_goal="Get into FAANG by Q3",
    )
    result = _format_memory_block(doc)
    assert "Target role: Senior Engineer, L5" in result
    assert "Target companies: Google, Meta" in result
    assert "Goal: Get into FAANG by Q3" in result


def test_format_weakest_skills_with_mistake() -> None:
    doc = _base_doc(
        weakest_skills=[
            {
                "skill": "System Design",
                "score": 40,
                "trend": "declining",
                "top_mistake": "no capacity planning",
            },
            {"skill": "Behavioral", "score": 50, "trend": "stable", "top_mistake": None},
        ]
    )
    result = _format_memory_block(doc)
    assert "Weakest areas" in result
    assert "System Design" in result
    assert "no capacity planning" in result
    assert "Behavioral" in result
    # No mistake marker for second skill (only one skill has top_mistake set)
    assert "declining) -- no capacity planning" in result
    assert "Behavioral (50, stable)" in result


def test_format_strongest_skills() -> None:
    doc = _base_doc(
        strongest_skills=[
            {"skill": "Communication", "score": 85, "trend": "improving"},
            {"skill": "Problem Solving", "score": 80, "trend": "stable"},
        ]
    )
    result = _format_memory_block(doc)
    assert "Strongest areas" in result
    assert "Communication" in result
    assert "improving" in result


def test_format_recurring_mistakes() -> None:
    doc = _base_doc(recurring_mistakes=["skips STAR format", "uses filler words"])
    result = _format_memory_block(doc)
    assert "Recurring mistakes" in result
    assert "skips STAR format" in result
    assert "uses filler words" in result


def test_format_stories_with_tip() -> None:
    doc = _base_doc(
        best_stories=[
            {
                "title": "Led platform migration",
                "best_score": 88,
                "competencies": ["leadership", "execution"],
                "tip": "emphasize the 40% reduction",
            }
        ]
    )
    result = _format_memory_block(doc)
    assert "Best stories" in result
    assert "Led platform migration" in result
    assert "score 88" in result
    assert "leadership, execution" in result
    assert "emphasize the 40% reduction" in result


def test_format_stories_without_tip() -> None:
    doc = _base_doc(
        best_stories=[{"title": "My story", "best_score": 75, "competencies": [], "tip": None}]
    )
    result = _format_memory_block(doc)
    assert "Tip:" not in result


def test_format_communication_notes() -> None:
    doc = _base_doc(communication_notes=["speaks too fast", "good eye contact"])
    result = _format_memory_block(doc)
    assert "Communication patterns" in result
    assert "speaks too fast" in result


def test_format_coaching_insights_as_dict() -> None:
    doc = _base_doc(coaching_insights=[{"insight": "needs structure", "evidence_count": 2}])
    result = _format_memory_block(doc)
    assert "Coaching notes" in result
    assert "needs structure" in result


def test_format_coaching_insights_as_string() -> None:
    doc = _base_doc(coaching_insights=["talks over interviewer"])
    result = _format_memory_block(doc)
    assert "talks over interviewer" in result


def test_format_current_focus() -> None:
    doc = _base_doc(current_focus="Practice STAR for leadership questions")
    result = _format_memory_block(doc)
    assert "Current focus: Practice STAR for leadership questions" in result


def test_format_stats_with_avg_score() -> None:
    doc = _base_doc(avg_score=72)
    result = _format_memory_block(doc)
    assert "average score 72" in result


def test_format_full_document_no_error() -> None:
    doc = {
        "total_sessions": 12,
        "target_role": "Staff Engineer",
        "target_level": "L6",
        "target_companies": ["Amazon"],
        "career_goal": "Principal in 2 years",
        "weakest_skills": [
            {"skill": "OO Design", "score": 45, "trend": "stable", "top_mistake": None}
        ],
        "strongest_skills": [{"skill": "Communication", "score": 90, "trend": "improving"}],
        "recurring_mistakes": ["no metrics"],
        "best_stories": [
            {"title": "Scaled payments", "best_score": 92, "competencies": ["scale"], "tip": None}
        ],
        "communication_notes": ["clear voice"],
        "coaching_insights": [{"insight": "add numbers", "evidence_count": 3}],
        "current_focus": "System design depth",
        "avg_score": 74,
    }
    result = _format_memory_block(doc)
    assert "MEMORY CONTEXT" in result
    assert len(result) > 200


# ── load_memory_context: Redis cache hit ─────────────────────────────────────


@pytest.mark.asyncio
async def test_load_memory_context_returns_cache_hit() -> None:
    user_id = uuid.uuid4()
    cached_block = "MEMORY CONTEXT -- RETURNING CANDIDATE:\nYou have coached..."

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=cached_block)

    db = AsyncMock()

    with patch("app.redis_client.get_redis", return_value=mock_redis):
        result = await load_memory_context(db, user_id)

    assert result == cached_block
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_load_memory_context_returns_none_on_cache_sentinel() -> None:
    user_id = uuid.uuid4()

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value="__NONE__")

    db = AsyncMock()

    with patch("app.redis_client.get_redis", return_value=mock_redis):
        result = await load_memory_context(db, user_id)

    assert result is None
    db.execute.assert_not_called()


# ── load_memory_context: DB paths ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_load_memory_context_returns_none_when_no_db_row() -> None:
    user_id = uuid.uuid4()

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    db = AsyncMock()
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=db_result)

    with patch("app.redis_client.get_redis", return_value=mock_redis):
        result = await load_memory_context(db, user_id)

    assert result is None


@pytest.mark.asyncio
async def test_load_memory_context_returns_formatted_block() -> None:
    user_id = uuid.uuid4()

    from app.models.user_memory import UserMemory

    memory = UserMemory(
        user_id=user_id,
        memory_document={
            "total_sessions": 3,
            "avg_score": 70,
            "recurring_mistakes": ["skips context"],
        },
        version=1,
        token_count=200,
        sessions_since_consolidation=3,
        batch_job_id=None,
    )

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()

    db = AsyncMock()
    result_mock = MagicMock()  # MagicMock so scalar_one_or_none() is sync
    result_mock.scalar_one_or_none.return_value = memory
    result_mock.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=result_mock)

    with patch("app.redis_client.get_redis", return_value=mock_redis):
        result = await load_memory_context(db, user_id)

    # total_sessions=3 with recurring_mistakes will format a block
    assert result is not None
    assert "MEMORY CONTEXT" in result
    assert "skips context" in result


@pytest.mark.asyncio
async def test_load_memory_context_returns_none_when_redis_unavailable() -> None:
    user_id = uuid.uuid4()

    db = AsyncMock()
    db_result = MagicMock()
    db_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=db_result)

    with patch("app.redis_client.get_redis", side_effect=Exception("redis down")):
        result = await load_memory_context(db, user_id)

    assert result is None
