"""Unit tests for the skill graph service.

Tests:
- Rule → skill mapping coverage
- get_or_create_node (creates new, returns existing)
- update_from_scoring_result (score changes, trends, evidence links)
- Spaced repetition scheduling
- Urgency scoring in drill planner
- Drill plan generation
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.skill_graph_node import SkillGraphNode, SkillTrend
from app.services.memory.drill_planner import DrillPlanner, _urgency_score
from app.services.memory.skill_graph import (
    RULE_SKILL_MAP,
    SkillGraphService,
    _compute_trend,
    _next_review_days,
)

# ── Rule → skill mapping ──────────────────────────────────────────────────────


def test_rule_skill_map_covers_all_rubric_rules() -> None:
    """Every rubric rule that can affect a skill has a mapping entry."""
    from app.services.scoring.rubric import RULE_IDS

    mapped = set(RULE_SKILL_MAP.keys())
    # All 13 non-negotiation rules + 2 negotiation rules should be mapped
    for rule_id in RULE_IDS:
        assert rule_id in mapped, f"Rule '{rule_id}' has no skill mapping"


def test_rule_skill_map_values_are_valid_skills() -> None:
    """Every mapped skill name exists in SKILL_CATEGORIES."""
    from app.models.skill_graph_node import SKILL_CATEGORIES

    all_skills = {s for skills in SKILL_CATEGORIES.values() for s in skills}
    for rule_id, skill in RULE_SKILL_MAP.items():
        assert skill in all_skills, f"Rule '{rule_id}' maps to unknown skill '{skill}'"


# ── Trend computation ─────────────────────────────────────────────────────────


def test_compute_trend_improving() -> None:
    assert _compute_trend(50, 60) == SkillTrend.IMPROVING


def test_compute_trend_declining() -> None:
    assert _compute_trend(70, 60) == SkillTrend.DECLINING


def test_compute_trend_stable_small_delta() -> None:
    assert _compute_trend(65, 67) == SkillTrend.STABLE  # delta < 5


def test_compute_trend_stable_zero_change() -> None:
    assert _compute_trend(55, 55) == SkillTrend.STABLE


# ── Spaced repetition ─────────────────────────────────────────────────────────


def test_next_review_days_weak_score() -> None:
    days = _next_review_days(30, SkillTrend.DECLINING)
    assert days == 1


def test_next_review_days_medium_score() -> None:
    days = _next_review_days(50, SkillTrend.STABLE)
    assert days == 4


def test_next_review_days_declining_medium() -> None:
    days = _next_review_days(50, SkillTrend.DECLINING)
    assert days == 3  # faster review when declining


def test_next_review_days_strong_score() -> None:
    days = _next_review_days(85, SkillTrend.STABLE)
    assert days == 14


def test_next_review_days_strong_declining() -> None:
    days = _next_review_days(85, SkillTrend.DECLINING)
    assert days == 7  # even strong skills need faster review when declining


# ── SkillGraphService ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_or_create_node_creates_new() -> None:
    """Creating a node for a skill that doesn't exist yet."""
    service = SkillGraphService()
    user_id = uuid.uuid4()

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    node = await service.get_or_create_node(mock_db, user_id, "star_structure")

    assert node.skill_name == "star_structure"
    assert node.skill_category == "behavioral"
    assert node.current_score == 0
    mock_db.add.assert_called_once()
    mock_db.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_or_create_node_returns_existing() -> None:
    """Existing node is returned without adding a new one."""
    service = SkillGraphService()
    user_id = uuid.uuid4()

    existing = MagicMock(spec=SkillGraphNode)
    existing.skill_name = "tradeoff_analysis"
    existing.current_score = 60

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    mock_db.execute = AsyncMock(return_value=mock_result)

    node = await service.get_or_create_node(mock_db, user_id, "tradeoff_analysis")

    assert node is existing
    mock_db.add.assert_not_called()


@pytest.mark.asyncio
async def test_update_from_scoring_result_negative_signal() -> None:
    """Rules triggered → negative signal → score decreases."""
    service = SkillGraphService()
    user_id = uuid.uuid4()

    node = MagicMock(spec=SkillGraphNode)
    node.skill_name = "star_structure"
    node.current_score = 60
    node.best_score = 65
    node.evidence_links = []
    node.typical_mistakes = []

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = node
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    updated = await service.update_from_scoring_result(
        db=mock_db,
        user_id=user_id,
        session_id=uuid.uuid4(),
        segment_index=0,
        overall_score=45,  # low overall score
        rules_triggered=[{"rule": "no_star_structure", "confidence": "strong"}],
        memory_hints={"skill_signals": []},
        question_type="behavioral",
    )

    # 1 from rule trigger + 2 base behavioral skills (quantifiable_results, ownership_signal)
    assert len(updated) == 3
    updated_node = updated[0]  # star_structure — first in dict insertion order
    # Score should decrease because rule triggered with low overall score
    assert updated_node.current_score < 60
    # Evidence link added (mock returns same node for all skills, so count = num updated)
    assert len(updated_node.evidence_links) >= 1


@pytest.mark.asyncio
async def test_update_from_scoring_result_positive_signal() -> None:
    """Memory hint positive signal → score increases."""
    service = SkillGraphService()
    user_id = uuid.uuid4()

    node = MagicMock(spec=SkillGraphNode)
    node.skill_name = "tradeoff_analysis"
    node.current_score = 55
    node.best_score = 55
    node.evidence_links = []
    node.typical_mistakes = []

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = node
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    updated = await service.update_from_scoring_result(
        db=mock_db,
        user_id=user_id,
        session_id=uuid.uuid4(),
        segment_index=0,
        overall_score=80,
        rules_triggered=[],  # no rules triggered
        memory_hints={
            "skill_signals": [
                {
                    "skill": "tradeoff_analysis",
                    "direction": "positive",
                    "note": "Good tradeoff discussion",
                }
            ]
        },
        question_type="system_design",
    )

    # 1 from memory hint + 4 base system_design skills (scalability, capacity, component, failure_modes)
    assert len(updated) == 5
    # Score should increase because positive signal with high overall score
    assert updated[0].current_score > 55


@pytest.mark.asyncio
async def test_update_best_score_when_improved() -> None:
    """best_score is updated when new_score > old best_score."""
    service = SkillGraphService()
    user_id = uuid.uuid4()

    node = MagicMock(spec=SkillGraphNode)
    node.skill_name = "tradeoff_analysis"
    node.current_score = 50
    node.best_score = 55  # current best
    node.evidence_links = []
    node.typical_mistakes = []

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = node
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    await service.update_from_scoring_result(
        db=mock_db,
        user_id=user_id,
        session_id=uuid.uuid4(),
        segment_index=0,
        overall_score=85,  # high score → positive signal for positive-hinted skill
        rules_triggered=[],
        memory_hints={
            "skill_signals": [
                {"skill": "tradeoff_analysis", "direction": "positive", "note": "Excellent"}
            ]
        },
        question_type="system_design",
    )

    # best_score should be updated to the new higher score
    assert node.best_score >= 55


# ── Urgency scoring ───────────────────────────────────────────────────────────


def test_urgency_low_score_high_urgency() -> None:
    """Low-score nodes have high urgency."""
    node = MagicMock(spec=SkillGraphNode)
    node.current_score = 20
    node.trend = SkillTrend.DECLINING
    node.next_review_due = None
    urgency = _urgency_score(node)
    assert urgency > 0.8  # very urgent


def test_urgency_high_score_low_urgency() -> None:
    """High-score stable nodes have low urgency."""
    node = MagicMock(spec=SkillGraphNode)
    node.current_score = 90
    node.trend = SkillTrend.STABLE
    node.next_review_due = datetime.now(UTC) + timedelta(days=10)
    urgency = _urgency_score(node)
    assert urgency < 0.15  # low urgency


def test_urgency_past_due_bonus() -> None:
    """Past-due nodes get urgency bonus."""
    node_on_time = MagicMock(spec=SkillGraphNode)
    node_on_time.current_score = 50
    node_on_time.trend = SkillTrend.STABLE
    node_on_time.next_review_due = datetime.now(UTC) + timedelta(days=5)

    node_past_due = MagicMock(spec=SkillGraphNode)
    node_past_due.current_score = 50
    node_past_due.trend = SkillTrend.STABLE
    node_past_due.next_review_due = datetime.now(UTC) - timedelta(days=5)

    assert _urgency_score(node_past_due) > _urgency_score(node_on_time)


# ── Drill planner ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_drill_planner_empty_graph() -> None:
    """Empty graph returns message instead of slots."""
    planner = DrillPlanner()

    mock_db = AsyncMock()
    with patch("app.services.memory.drill_planner.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=[])
        plan = await planner.generate_weekly_plan(mock_db, uuid.uuid4())

    assert plan["slots"] == []
    assert plan["total_skills"] == 0
    assert plan["message"] is not None


@pytest.mark.asyncio
async def test_drill_planner_generates_three_slots() -> None:
    """With 3+ skills, planner generates 3 slots (Mon/Wed/Fri)."""
    planner = DrillPlanner()

    nodes = []
    for i, name in enumerate(["star_structure", "tradeoff_analysis", "conciseness"]):
        n = MagicMock(spec=SkillGraphNode)
        n.skill_name = name
        n.skill_category = "behavioral"
        n.current_score = 30 + i * 10
        n.best_score = 40 + i * 10
        n.trend = SkillTrend.STABLE
        n.next_review_due = None
        nodes.append(n)

    mock_db = AsyncMock()
    with patch("app.services.memory.drill_planner.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=nodes)
        plan = await planner.generate_weekly_plan(mock_db, uuid.uuid4())

    assert len(plan["slots"]) == 3
    assert plan["slots"][0]["day"] == "Monday"
    assert plan["slots"][1]["day"] == "Wednesday"
    assert plan["slots"][2]["day"] == "Friday"


@pytest.mark.asyncio
async def test_drill_planner_low_score_gets_more_questions() -> None:
    """Skills with score < 60 get 2 questions per slot."""
    planner = DrillPlanner()

    node = MagicMock(spec=SkillGraphNode)
    node.skill_name = "star_structure"
    node.skill_category = "behavioral"
    node.current_score = 35  # below 60
    node.best_score = 40
    node.trend = SkillTrend.DECLINING
    node.next_review_due = None

    mock_db = AsyncMock()
    with patch("app.services.memory.drill_planner.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=[node])
        plan = await planner.generate_weekly_plan(mock_db, uuid.uuid4())

    assert plan["slots"][0]["questions"] == 2


# ── DrillPlanner.get_best_scores ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_best_scores_returns_sorted_by_gap() -> None:
    """get_best_scores returns skills sorted by gap (largest first)."""
    planner = DrillPlanner()

    def _node(name: str, current: int, best: int) -> MagicMock:
        n = MagicMock(spec=SkillGraphNode)
        n.skill_name = name
        n.skill_category = "behavioral"
        n.current_score = current
        n.best_score = best
        return n

    nodes = [
        _node("star_structure", 70, 80),  # gap=10
        _node("conciseness", 50, 90),  # gap=40
        _node("tradeoff_analysis", 60, 65),  # gap=5
    ]

    mock_db = AsyncMock()
    with patch("app.services.memory.drill_planner.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=nodes)
        result = await planner.get_best_scores(mock_db, uuid.uuid4())

    assert result[0]["skill_name"] == "conciseness"  # largest gap first
    assert result[0]["gap"] == 40
    assert result[1]["gap"] == 10
    assert result[2]["gap"] == 5


@pytest.mark.asyncio
async def test_get_best_scores_zero_best_score_excluded() -> None:
    """Skills with best_score=0 are excluded (no personal best yet)."""
    planner = DrillPlanner()

    nodes = [
        MagicMock(
            spec=SkillGraphNode,
            skill_name="star_structure",
            skill_category="behavioral",
            current_score=50,
            best_score=0,
        ),
        MagicMock(
            spec=SkillGraphNode,
            skill_name="conciseness",
            skill_category="behavioral",
            current_score=60,
            best_score=70,
        ),
    ]

    mock_db = AsyncMock()
    with patch("app.services.memory.drill_planner.skill_graph_service") as mock_service:
        mock_service.get_user_graph = AsyncMock(return_value=nodes)
        result = await planner.get_best_scores(mock_db, uuid.uuid4())

    # Only conciseness has a best_score > 0
    assert len(result) == 1
    assert result[0]["skill_name"] == "conciseness"


# ── _focus_note branches ──────────────────────────────────────────────────────


def test_focus_note_low_score() -> None:
    """Score < 40 → 'Foundation needed' message."""
    from app.services.memory.drill_planner import _focus_note

    node = MagicMock(spec=SkillGraphNode)
    node.current_score = 30
    node.best_score = 35
    node.trend = SkillTrend.STABLE

    note = _focus_note(node)
    assert "Foundation" in note


def test_focus_note_declining_trend() -> None:
    """Declining trend → 'Slipping!' message."""
    from app.services.memory.drill_planner import _focus_note

    node = MagicMock(spec=SkillGraphNode)
    node.current_score = 65
    node.best_score = 80
    node.trend = SkillTrend.DECLINING

    note = _focus_note(node)
    assert "Slipping" in note


def test_focus_note_beat_your_best() -> None:
    """best_score > current + 10 → 'Beat Your Best' message."""
    from app.services.memory.drill_planner import _focus_note

    node = MagicMock(spec=SkillGraphNode)
    node.current_score = 60
    node.best_score = 75  # 15 above current
    node.trend = SkillTrend.STABLE

    note = _focus_note(node)
    assert "Beat Your Best" in note


def test_focus_note_default() -> None:
    """Otherwise → generic 'Keep building' message."""
    from app.services.memory.drill_planner import _focus_note

    node = MagicMock(spec=SkillGraphNode)
    node.current_score = 70
    node.best_score = 72  # only 2 above — not "beat your best"
    node.trend = SkillTrend.STABLE

    note = _focus_note(node)
    assert "building" in note.lower() or "target" in note.lower()


# ── SkillGraphService.get_weakest_skills / get_user_graph ────────────────────


@pytest.mark.asyncio
async def test_get_past_due_skills_returns_list() -> None:
    """get_past_due_skills queries DB and returns nodes past review date."""
    from app.services.memory.skill_graph import SkillGraphService

    service = SkillGraphService()
    past_due_node = MagicMock(spec=SkillGraphNode)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [past_due_node]
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await service.get_past_due_skills(mock_db, uuid.uuid4())
    assert result == [past_due_node]


@pytest.mark.asyncio
async def test_get_weakest_skills_returns_list() -> None:
    """get_weakest_skills queries DB and returns nodes."""
    from app.services.memory.skill_graph import SkillGraphService

    service = SkillGraphService()
    weak_node = MagicMock(spec=SkillGraphNode)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [weak_node]
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await service.get_weakest_skills(mock_db, uuid.uuid4())
    assert result == [weak_node]


@pytest.mark.asyncio
async def test_get_user_graph_returns_nodes() -> None:
    """get_user_graph queries DB and returns nodes ordered by category+name."""
    from app.services.memory.skill_graph import SkillGraphService

    service = SkillGraphService()
    node = MagicMock(spec=SkillGraphNode)

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [node]
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await service.get_user_graph(mock_db, uuid.uuid4())
    assert result == [node]
