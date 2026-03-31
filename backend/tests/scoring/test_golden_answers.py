"""Golden answer test suite for the scoring engine.

Two tiers:
  Unit (default, no API keys needed):
    - Rubric loading smoke tests
    - Scorer instantiation and _extract_qa_segments
    - Mock scorer returns deterministic results

  Integration (@pytest.mark.integration — requires ANTHROPIC_API_KEY):
    - Lite: 10 cases × 3 runs (CI gate)
    - Full: all cases × 5 runs (nightly gate, @pytest.mark.nightly)
    - Variance target: < 10 points per answer across runs

Run lite:   pytest tests/scoring/ -m "not nightly" -x
Run full:   pytest tests/scoring/ -m nightly
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.scoring import _extract_qa_segments
from app.services.scoring.rubric import (
    RUBRIC_PROMPT_PREFIX,
    RULE_IDS,
    RULES,
    RULES_BY_ID,
    rules_for_question_type,
)
from app.services.scoring.scorer import Scorer, _build_dynamic_prompt

# ── Load golden answer data ────────────────────────────────────────────────────

_GOLDEN_FILE = Path(__file__).parent / "golden_answers.json"

with _GOLDEN_FILE.open() as f:
    GOLDEN_SET: list[dict[str, Any]] = json.load(f)

# Lite suite: first 10 cases (default CI)
LITE_SET = GOLDEN_SET[:10]


# ── Rubric smoke tests ─────────────────────────────────────────────────────────


def test_rubric_has_15_rules() -> None:
    """Rubric must have exactly 15 rules as per spec."""
    assert len(RULES) == 15, f"Expected 15 rules, got {len(RULES)}"


def test_all_rule_ids_unique() -> None:
    """No duplicate rule IDs."""
    assert len(RULE_IDS) == len(set(RULE_IDS))


def test_rules_by_id_covers_all() -> None:
    """RULES_BY_ID lookup covers every rule."""
    for rule in RULES:
        assert rule.id in RULES_BY_ID
        assert RULES_BY_ID[rule.id] is rule


def test_rule_categories() -> None:
    """All rules have valid categories."""
    valid = {"structure", "depth", "communication", "seniority_signal"}
    for rule in RULES:
        assert rule.category in valid, f"{rule.id} has invalid category: {rule.category}"


def test_rules_for_behavioral() -> None:
    """Behavioral questions get at least 8 applicable rules."""
    behavioral_rules = rules_for_question_type("behavioral")
    assert len(behavioral_rules) >= 8


def test_rules_for_system_design() -> None:
    """System design questions get at least 6 rules."""
    sd_rules = rules_for_question_type("system_design")
    assert len(sd_rules) >= 6


def test_rules_for_negotiation_includes_negotiation_rules() -> None:
    """Negotiation questions include the negotiation-specific rules."""
    neg_rules = rules_for_question_type("negotiation")
    neg_rule_ids = {r.id for r in neg_rules}
    assert "weak_anchor" in neg_rule_ids
    assert "early_concession" in neg_rule_ids


def test_rubric_prompt_prefix_not_empty() -> None:
    """Cached rubric prefix must be substantial (>500 chars)."""
    assert len(RUBRIC_PROMPT_PREFIX) > 500


def test_rubric_prompt_prefix_contains_all_rule_ids() -> None:
    """Every rule ID appears in the prompt prefix."""
    for rule_id in RULE_IDS:
        assert rule_id in RUBRIC_PROMPT_PREFIX, (
            f"Rule ID '{rule_id}' not found in RUBRIC_PROMPT_PREFIX"
        )


# ── Scorer unit tests (mocked Anthropic) ──────────────────────────────────────


def test_extract_qa_segments_empty() -> None:
    """Empty transcript returns empty segments."""
    assert _extract_qa_segments([]) == []


def test_extract_qa_segments_single_qa() -> None:
    """Single assistant + user turn with enough words = one segment."""
    answer = (
        "I am a senior engineer with eight years of experience building distributed systems "
        "at scale across multiple cloud providers and leading cross-functional teams."
    )
    transcript = [
        {"role": "assistant", "content": "Tell me about yourself.", "ts_ms": 0},
        {"role": "user", "content": answer, "ts_ms": 1000},
    ]
    segs = _extract_qa_segments(transcript)
    assert len(segs) == 1
    question, answer_turns = segs[0]
    assert question == "Tell me about yourself."
    assert len(answer_turns) == 1
    assert answer_turns[0]["content"] == answer


def test_extract_qa_segments_short_answer_skipped() -> None:
    """User answers with fewer than 15 words are skipped (greetings filter)."""
    transcript = [
        {"role": "assistant", "content": "Tell me about yourself.", "ts_ms": 0},
        {"role": "user", "content": "I am a senior engineer.", "ts_ms": 1000},
    ]
    segs = _extract_qa_segments(transcript)
    assert len(segs) == 0


def test_extract_qa_segments_multiple() -> None:
    """Multiple Q&A pairs all captured when answers meet the word minimum."""
    long_a1 = "I tackled this by first identifying the root cause and then systematically addressing each bottleneck"
    long_a1_cont = (
        "which ultimately reduced latency by forty percent across all production services"
    )
    long_a2 = "In that situation I worked closely with the team to define clear ownership and measurable goals for each sprint"
    transcript = [
        {"role": "assistant", "content": "Q1?", "ts_ms": 0},
        {"role": "user", "content": long_a1, "ts_ms": 1000},
        {"role": "user", "content": long_a1_cont, "ts_ms": 2000},
        {"role": "assistant", "content": "Q2?", "ts_ms": 3000},
        {"role": "user", "content": long_a2, "ts_ms": 4000},
    ]
    segs = _extract_qa_segments(transcript)
    assert len(segs) == 2
    assert segs[0][0] == "Q1?"
    assert len(segs[0][1]) == 2  # 2 user turns
    assert segs[1][0] == "Q2?"
    assert len(segs[1][1]) == 1


def test_extract_qa_segments_no_user_turns() -> None:
    """Question with no user answer not included (incomplete segment)."""
    transcript = [
        {"role": "assistant", "content": "Tell me about yourself.", "ts_ms": 0},
    ]
    segs = _extract_qa_segments(transcript)
    assert len(segs) == 0


def test_build_dynamic_prompt_contains_question() -> None:
    """Dynamic prompt includes the question text."""
    prompt = _build_dynamic_prompt(
        question="Tell me about a challenge.",
        answer_text="I fixed a bug.",
        answer_transcript=[{"role": "user", "content": "I fixed a bug.", "ts_ms": 0}],
        target_level="L5",
        rule_ids_note="Applicable rules: all",
    )
    assert "Tell me about a challenge." in prompt
    assert "L5" in prompt


@pytest.mark.asyncio
async def test_scorer_calls_anthropic_and_returns_result() -> None:
    """Scorer with a mocked Anthropic client returns a ScoringResult."""
    mock_result = {
        "overall_score": 65,
        "confidence": "medium",
        "rules_triggered": [
            {
                "rule": "missing_metrics",
                "confidence": "strong",
                "evidence": {"start_ms": 1000, "end_ms": 3000},
                "fix": "Add specific numbers.",
                "impact": "+10 to Structure",
            }
        ],
        "categories": {
            "structure": 60,
            "depth": 70,
            "communication": 75,
            "seniority_signal": 55,
        },
        "level_assessment": {
            "l4": "pass",
            "l5": "borderline",
            "l6": "fail",
            "gaps": ["Missing tradeoff discussion"],
        },
        "diff_versions": {
            "minimal": {
                "text": "...with 40% improvement...",
                "changes": [],
                "estimated_new_score": 75,
            },
            "medium": {
                "text": "Rewritten answer...",
                "changes": [],
                "estimated_new_score": 82,
            },
            "ideal": {
                "text": "Ideal answer...",
                "changes": [],
                "estimated_new_score": 92,
            },
        },
        "memory_hints": {
            "skill_signals": [],
            "story_detected": False,
            "story_title": None,
            "communication_notes": None,
        },
    }

    mock_usage = MagicMock()
    mock_usage.input_tokens = 500
    mock_usage.output_tokens = 800
    mock_usage.cache_read_input_tokens = 300  # prompt cache hit

    mock_block = MagicMock()
    mock_block.type = "tool_use"
    mock_block.name = "structured_output"
    mock_block.input = mock_result

    mock_response = MagicMock()
    mock_response.content = [mock_block]
    mock_response.usage = mock_usage
    mock_response.stop_reason = "tool_use"

    mock_db = AsyncMock()
    # No transcript words — evidence quotes will be None
    mock_words_result = MagicMock()
    mock_words_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_words_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    scorer = Scorer(api_key="test-key", quality_profile="balanced")

    with patch.object(scorer._client.messages, "create", new=AsyncMock(return_value=mock_response)):
        result = await scorer.score_segment(
            session_id=uuid.uuid4(),
            segment_index=0,
            question="Tell me about a challenge.",
            answer_transcript=[
                {"role": "assistant", "content": "Tell me about a challenge.", "ts_ms": 0},
                {"role": "user", "content": "I fixed a slow query.", "ts_ms": 1000},
            ],
            question_type="behavioral",
            target_level="L5",
            db=mock_db,
            user_id=uuid.uuid4(),
        )

    assert result.overall_score == 65
    assert result.confidence == "medium"
    assert len(result.rules_triggered) == 1
    assert result.rules_triggered[0]["rule"] == "missing_metrics"
    assert result.cached_tokens == 300
    assert result.retries_used == 0


@pytest.mark.asyncio
async def test_scorer_retries_on_no_tool_use_block() -> None:
    """Scorer retries when Anthropic returns no tool_use block, then succeeds."""
    good_result = {
        "overall_score": 70,
        "confidence": "medium",
        "rules_triggered": [],
        "categories": {"structure": 70, "depth": 70, "communication": 70, "seniority_signal": 70},
        "level_assessment": {"l4": "pass", "l5": "borderline", "l6": "fail", "gaps": []},
        "diff_versions": {
            "minimal": {"text": "...", "changes": [], "estimated_new_score": 75},
            "medium": {"text": "...", "changes": [], "estimated_new_score": 80},
            "ideal": {"text": "...", "changes": [], "estimated_new_score": 90},
        },
        "memory_hints": {
            "skill_signals": [],
            "story_detected": False,
            "story_title": None,
            "communication_notes": None,
        },
    }

    mock_usage = MagicMock()
    mock_usage.input_tokens = 400
    mock_usage.output_tokens = 600
    mock_usage.cache_read_input_tokens = 0

    # First call: no tool_use block (simulates parse failure)
    bad_text_block = MagicMock()
    bad_text_block.type = "text"

    bad_response = MagicMock()
    bad_response.content = [bad_text_block]
    bad_response.usage = mock_usage
    bad_response.stop_reason = "end_turn"

    # Second call: valid tool_use block
    good_block = MagicMock()
    good_block.type = "tool_use"
    good_block.name = "structured_output"
    good_block.input = good_result

    good_response = MagicMock()
    good_response.content = [good_block]
    good_response.usage = mock_usage
    good_response.stop_reason = "tool_use"

    mock_db = AsyncMock()
    mock_words_result = MagicMock()
    mock_words_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_words_result)
    mock_db.add = MagicMock()

    scorer = Scorer(api_key="test-key", quality_profile="balanced")

    call_count = 0

    async def _mock_create(**kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        return bad_response if call_count == 1 else good_response

    with patch.object(scorer._client.messages, "create", side_effect=_mock_create):
        result = await scorer.score_segment(
            session_id=uuid.uuid4(),
            segment_index=0,
            question="Q?",
            answer_transcript=[{"role": "user", "content": "A", "ts_ms": 0}],
            question_type="behavioral",
            target_level="L5",
            db=mock_db,
            user_id=uuid.uuid4(),
        )

    assert result.overall_score == 70
    assert result.retries_used == 1
    assert call_count == 2


# ── Integration tests (require real Anthropic API key) ────────────────────────


@pytest.fixture
def anthropic_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping integration test")
    return key


@pytest.mark.integration
@pytest.mark.parametrize("case", LITE_SET[:10])
@pytest.mark.asyncio
async def test_golden_answer_lite(case: dict[str, Any], anthropic_api_key: str) -> None:
    """Lite: each golden answer scored 3 times; variance < 10; score in expected range."""
    scorer = Scorer(api_key=anthropic_api_key, quality_profile="balanced")
    runs = 3

    mock_db = AsyncMock()
    mock_words_result = MagicMock()
    mock_words_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_words_result)
    mock_db.add = MagicMock()

    transcript = [
        {"role": "assistant", "content": case["question"], "ts_ms": 0},
        {"role": "user", "content": case["answer"], "ts_ms": 1000},
    ]

    scores: list[int] = []
    for _ in range(runs):
        result = await scorer.score_segment(
            session_id=uuid.uuid4(),
            segment_index=0,
            question=case["question"],
            answer_transcript=transcript,
            question_type=case.get("question_type", "behavioral"),
            target_level="L5",
            db=mock_db,
            user_id=uuid.uuid4(),
        )
        scores.append(result.overall_score)

    lo, hi = case["expected_score_range"]
    variance = max(scores) - min(scores)

    assert variance < 10, f"[{case['id']}] Variance {variance} too high. Scores: {scores}"
    for s in scores:
        assert lo <= s <= hi, f"[{case['id']}] Score {s} outside [{lo}, {hi}]. All scores: {scores}"


@pytest.mark.integration
@pytest.mark.nightly
@pytest.mark.parametrize("case", GOLDEN_SET)
@pytest.mark.asyncio
async def test_golden_answer_full(case: dict[str, Any], anthropic_api_key: str) -> None:
    """Nightly: all golden answers × 5 runs; variance < 10; score in expected range."""
    scorer = Scorer(api_key=anthropic_api_key, quality_profile="balanced")
    runs = 5

    mock_db = AsyncMock()
    mock_words_result = MagicMock()
    mock_words_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_words_result)
    mock_db.add = MagicMock()

    transcript = [
        {"role": "assistant", "content": case["question"], "ts_ms": 0},
        {"role": "user", "content": case["answer"], "ts_ms": 1000},
    ]

    scores: list[int] = []
    for _ in range(runs):
        result = await scorer.score_segment(
            session_id=uuid.uuid4(),
            segment_index=0,
            question=case["question"],
            answer_transcript=transcript,
            question_type=case.get("question_type", "behavioral"),
            target_level="L5",
            db=mock_db,
            user_id=uuid.uuid4(),
        )
        scores.append(result.overall_score)

    lo, hi = case["expected_score_range"]
    variance = max(scores) - min(scores)

    assert variance < 10, f"[{case['id']}] Variance {variance} too high. Scores: {scores}"
    for s in scores:
        assert lo <= s <= hi, f"[{case['id']}] Score {s} outside [{lo}, {hi}]. All scores: {scores}"
