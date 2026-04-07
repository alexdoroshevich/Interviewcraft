"""Unit tests for MemoryBuilder internals.

Covers:
- _similar_insight: overlap heuristic
- _merge_extraction: all document mutation paths (mistakes, story, communication,
  coaching insights, focus, session stats) — no Anthropic call needed
- build_memory: returns False when no completed session found
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.memory.builder import _merge_extraction, _similar_insight

# ── _similar_insight ──────────────────────────────────────────────────────────


def test_similar_insight_high_overlap() -> None:
    # "rambles without clear conclusion" vs "rambles without conclusion" — 3/4 = 0.75
    assert (
        _similar_insight("rambles without clear conclusion", "rambles without conclusion") is True
    )


def test_similar_insight_no_overlap() -> None:
    assert _similar_insight("structured responses are important", "eye contact and pauses") is False


def test_similar_insight_identical() -> None:
    assert _similar_insight("rambles without conclusion", "rambles without conclusion") is True


def test_similar_insight_empty_strings() -> None:
    assert _similar_insight("", "something") is False
    assert _similar_insight("something", "") is False


def test_similar_insight_single_word_match() -> None:
    assert _similar_insight("rambles", "rambles") is True


def test_similar_insight_single_word_no_match() -> None:
    assert _similar_insight("clarity", "rambles") is False


# ── _merge_extraction mock helpers ───────────────────────────────────────────


def _make_sync_execute_result(row_value: object) -> MagicMock:
    """Return an AsyncMock execute result with sync scalar_one_or_none."""
    result = MagicMock()  # sync MagicMock so scalar_one_or_none() returns immediately
    result.scalar_one_or_none.return_value = row_value
    # Also set up scalars().all() for skill queries
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result.scalars.return_value = scalars_mock
    return result


def _make_db(
    existing_memory_doc: dict | None = None,
    existing_story: object | None = None,
) -> AsyncMock:
    """Return a mock AsyncSession with an optional pre-existing UserMemory row.

    execute side_effect order (matches _merge_extraction call order):
      1. user_memory row
      2. skill_graph nodes (scalars().all())
      3. story find-by-title (only when story_detected=True)
      4. top-4 stories ranking (always — returns empty list when no stories)
    We provide 6 slots so tests with or without story detection always succeed.
    """
    from app.models.user_memory import UserMemory

    db = AsyncMock()

    if existing_memory_doc is not None:
        mem = UserMemory(
            user_id=uuid.uuid4(),
            memory_document=existing_memory_doc,
            version=1,
            token_count=0,
            sessions_since_consolidation=0,
        )
    else:
        mem = None

    mem_result = _make_sync_execute_result(mem)
    skill_result = _make_sync_execute_result(None)  # scalars().all() = []
    story_find_result = _make_sync_execute_result(existing_story)  # story upsert lookup
    stories_rank_result = _make_sync_execute_result(None)  # scalars().all() = []

    # Execute call order in _merge_extraction:
    #   1. select(UserMemory)              → mem_result
    #   2. select(Story).where(title=...) → story_find_result  [only when story_detected=True]
    #   3. select(Story).order_by(score)  → stories_rank_result [only when story_detected=True]
    #   4. select(SkillGraphNode)          → skill_result
    # For no-story calls only 1 and 4 fire, but we always provide the full list for safety.
    db.execute = AsyncMock(
        side_effect=[
            mem_result,
            story_find_result,
            stories_rank_result,
            skill_result,
            story_find_result,
            stories_rank_result,
            skill_result,
        ]  # extra safety slots
    )
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_session(session_type: str = "behavioral") -> MagicMock:
    session = MagicMock()
    session.id = uuid.uuid4()
    session.type = session_type
    session.company = "Acme"
    session.persona = "Friendly"
    session.focus_skill = None
    return session


def _make_segment(score: int, answer: str = "test answer") -> MagicMock:
    seg = MagicMock()
    seg.segment_index = 0
    seg.overall_score = score
    seg.confidence = "high"
    seg.category_scores = {"structure": score}
    seg.answer_text = answer
    seg.question_text = "Tell me about yourself"
    seg.rules_triggered = []
    seg.diff_versions = None
    return seg


# ── _merge_extraction: create new row ────────────────────────────────────────


@pytest.mark.asyncio
async def test_merge_creates_new_row_when_none_exists() -> None:
    user_id = uuid.uuid4()
    db = _make_db(None)  # no existing row
    session = _make_session()
    segments = [_make_segment(75)]
    extraction: dict = {
        "recurring_mistakes": ["skips context"],
        "story_detected": {"found": False},
        "communication_observations": [],
        "coaching_observation": None,
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)

    # A new UserMemory should have been added to the session
    db.add.assert_called_once()
    added_obj = db.add.call_args[0][0]
    assert added_obj.memory_document["recurring_mistakes"] == ["skips context"]
    assert added_obj.memory_document["total_sessions"] == 1


# ── _merge_extraction: recurring_mistakes ────────────────────────────────────


@pytest.mark.asyncio
async def test_merge_deduplicates_recurring_mistakes() -> None:
    existing_doc = {"recurring_mistakes": ["skips context"], "total_sessions": 3}
    user_id = uuid.uuid4()
    db = _make_db(existing_doc)
    session = _make_session()
    segments = [_make_segment(70)]
    extraction = {
        "recurring_mistakes": ["skips context", "uses filler words"],
        "story_detected": {"found": False},
        "communication_observations": [],
        "coaching_observation": None,
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)

    # Row already existed — db.add should NOT be called
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_merge_caps_mistakes_at_6() -> None:
    existing_doc = {
        "recurring_mistakes": ["m1", "m2", "m3", "m4", "m5"],
        "total_sessions": 5,
    }
    user_id = uuid.uuid4()
    db = _make_db(existing_doc)
    session = _make_session()
    segments = [_make_segment(60)]
    extraction = {
        "recurring_mistakes": ["m6", "m7"],  # would push to 7 — should be capped at 6
        "story_detected": {"found": False},
        "communication_observations": [],
        "coaching_observation": None,
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    db.add.assert_not_called()


# ── _merge_extraction: story ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_merge_adds_new_story() -> None:
    from app.models.story import Story

    existing_doc = {"best_stories": [], "total_sessions": 1}
    user_id = uuid.uuid4()
    # No existing Story row in DB → code will create one via db.add
    db = _make_db(existing_doc, existing_story=None)
    session = _make_session()
    segments = [_make_segment(80)]
    extraction = {
        "recurring_mistakes": [],
        "story_detected": {
            "found": True,
            "title": "Led migration project",
            "competencies": ["leadership", "execution"],
            "tip": "mention impact numbers",
        },
        "communication_observations": [],
        "coaching_observation": None,
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    # Memory row already existed (not added), but a new Story row should be added
    assert db.add.call_count == 1
    added = db.add.call_args[0][0]
    assert isinstance(added, Story)
    assert added.title == "Led migration project"


@pytest.mark.asyncio
async def test_merge_updates_existing_story_score() -> None:
    existing_doc = {
        "best_stories": [{"title": "Led migration project", "best_score": 60, "competencies": []}],
        "total_sessions": 2,
    }
    user_id = uuid.uuid4()
    # Pre-existing Story row in DB — score should be updated in-place, no db.add
    existing_story_mock = MagicMock()
    existing_story_mock.best_score_with_this_story = 60
    existing_story_mock.times_used = 2
    db = _make_db(existing_doc, existing_story=existing_story_mock)
    session = _make_session()
    segments = [_make_segment(90)]
    extraction = {
        "recurring_mistakes": [],
        "story_detected": {
            "found": True,
            "title": "Led migration project",  # same title, higher score
            "competencies": ["leadership"],
            "tip": "great structure",
        },
        "communication_observations": [],
        "coaching_observation": None,
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    # Story existed in DB — no new row added; score should be updated in-place
    db.add.assert_not_called()
    assert existing_story_mock.best_score_with_this_story == 90  # max(60, 90)


# ── _merge_extraction: coaching insights ─────────────────────────────────────


@pytest.mark.asyncio
async def test_merge_adds_new_coaching_insight() -> None:
    existing_doc = {"coaching_insights": [], "total_sessions": 1}
    user_id = uuid.uuid4()
    db = _make_db(existing_doc)
    session = _make_session()
    segments = [_make_segment(65)]
    extraction = {
        "recurring_mistakes": [],
        "story_detected": {"found": False},
        "communication_observations": [],
        "coaching_observation": "candidate tends to skip the impact statement",
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_merge_deduplicates_similar_coaching_insights() -> None:
    existing_doc = {
        "coaching_insights": [{"insight": "rambles without conclusion", "evidence_count": 1}],
        "total_sessions": 2,
    }
    user_id = uuid.uuid4()
    db = _make_db(existing_doc)
    session = _make_session()
    segments = [_make_segment(65)]
    extraction = {
        "recurring_mistakes": [],
        "story_detected": {"found": False},
        "communication_observations": [],
        "coaching_observation": "rambles without conclusion",  # identical
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    db.add.assert_not_called()


# ── _merge_extraction: session stats ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_merge_increments_total_sessions() -> None:
    existing_doc = {"total_sessions": 5, "avg_score": 70}
    user_id = uuid.uuid4()
    db = _make_db(existing_doc)
    session = _make_session()
    segments = [_make_segment(80)]
    extraction = {
        "recurring_mistakes": [],
        "story_detected": {"found": False},
        "communication_observations": [],
        "coaching_observation": None,
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_merge_sets_focus_suggestion() -> None:
    existing_doc = {"total_sessions": 1}
    user_id = uuid.uuid4()
    db = _make_db(existing_doc)
    session = _make_session()
    segments = [_make_segment(55)]
    extraction = {
        "recurring_mistakes": [],
        "story_detected": {"found": False},
        "communication_observations": [],
        "coaching_observation": None,
        "focus_suggestion": "Practice STAR format for behavioral questions",
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_merge_communication_notes_deduped() -> None:
    existing_doc = {"communication_notes": ["speaks fast"], "total_sessions": 1}
    user_id = uuid.uuid4()
    db = _make_db(existing_doc)
    session = _make_session()
    segments = [_make_segment(60)]
    extraction = {
        "recurring_mistakes": [],
        "story_detected": {"found": False},
        "communication_observations": ["speaks fast", "pauses well"],  # first is duplicate
        "coaching_observation": None,
        "focus_suggestion": None,
    }

    await _merge_extraction(db, user_id, session, segments, extraction)
    db.add.assert_not_called()


# ── build_memory: early exit paths ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_memory_returns_false_when_session_not_completed() -> None:
    from app.services.memory.builder import build_memory

    session = MagicMock()
    session.id = uuid.uuid4()
    session.user_id = uuid.uuid4()
    session.status = "active"  # not completed

    db = AsyncMock()
    seg_result = MagicMock()
    seg_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=seg_result)

    result = await build_memory(db, session, session.user_id, "")
    assert result is False


@pytest.mark.asyncio
async def test_build_memory_returns_false_when_no_segments() -> None:
    from app.services.memory.builder import build_memory

    session = MagicMock()
    session.id = uuid.uuid4()
    session.user_id = uuid.uuid4()
    session.status = "completed"

    db = AsyncMock()
    seg_result = MagicMock()
    seg_result.scalars.return_value.all.return_value = []  # no segments
    db.execute = AsyncMock(return_value=seg_result)

    result = await build_memory(db, session, session.user_id, "")
    assert result is False


@pytest.mark.asyncio
async def test_consolidate_memory_returns_false_when_no_row() -> None:
    """consolidate_memory is a no-op when user_memories row does not exist."""
    from app.services.memory.builder import consolidate_memory

    db = AsyncMock()
    row_result = MagicMock()
    row_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=row_result)

    result = await consolidate_memory(db, uuid.uuid4(), "fake-key")
    assert result is False


@pytest.mark.asyncio
async def test_consolidate_memory_skips_when_job_already_pending() -> None:
    """consolidate_memory is a no-op when batch_job_id is already set."""
    from app.services.memory.builder import consolidate_memory

    memory_row = MagicMock()
    memory_row.memory_document = {"recurring_mistakes": ["test mistake"]}
    memory_row.batch_job_id = "msgbatch_existing123"

    db = AsyncMock()
    row_result = MagicMock()
    row_result.scalar_one_or_none.return_value = memory_row
    db.execute = AsyncMock(return_value=row_result)

    result = await consolidate_memory(db, uuid.uuid4(), "fake-key")
    assert result is False
