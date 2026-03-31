"""Unit tests for scorer helper functions.

Covers:
- _coerce_json_fields: dict/list fields that LLM returns as JSON strings
- _fill_evidence_quotes: quote extraction from transcript_words
- Scorer: retry logic, ideal diff missing stub, max retries exceeded
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scoring.scorer import (
    Scorer,
    _coerce_json_fields,
    _fill_evidence_quotes,
)

# ── _coerce_json_fields ────────────────────────────────────────────────────────


def test_coerce_json_fields_dict_as_string() -> None:
    """Dict field returned as a JSON string gets parsed back into a dict."""
    inner = {"minimal": {"text": "answer", "changes": [], "estimated_new_score": 80}}
    result = {
        "diff_versions": json.dumps(inner),
        "categories": json.dumps({"technical": 70}),
    }
    coerced = _coerce_json_fields(result)
    assert isinstance(coerced["diff_versions"], dict)
    assert coerced["diff_versions"] == inner
    assert isinstance(coerced["categories"], dict)


def test_coerce_json_fields_list_as_string() -> None:
    """List field (rules_triggered) returned as JSON string gets parsed back."""
    rules = [{"rule_id": "R1", "triggered": True}]
    result = {"rules_triggered": json.dumps(rules)}
    coerced = _coerce_json_fields(result)
    assert isinstance(coerced["rules_triggered"], list)
    assert coerced["rules_triggered"] == rules


def test_coerce_json_fields_invalid_json_string_becomes_empty_dict() -> None:
    """Invalid JSON string for a dict field → empty dict (no crash)."""
    result = {"categories": "not-valid-json{{{"}
    coerced = _coerce_json_fields(result)
    assert coerced["categories"] == {}


def test_coerce_json_fields_invalid_json_list_becomes_empty_list() -> None:
    """Invalid JSON string for rules_triggered → empty list (no crash)."""
    result = {"rules_triggered": "[broken"}
    coerced = _coerce_json_fields(result)
    assert coerced["rules_triggered"] == []


def test_coerce_json_fields_valid_dict_unchanged() -> None:
    """Already-dict fields are not re-parsed."""
    original = {"key": "value"}
    result = {"diff_versions": original}
    coerced = _coerce_json_fields(result)
    assert coerced["diff_versions"] is original


def test_coerce_json_fields_none_value_unchanged() -> None:
    """None values pass through without error."""
    result = {"categories": None, "diff_versions": None}
    coerced = _coerce_json_fields(result)
    assert coerced["categories"] is None


# ── _fill_evidence_quotes ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_fill_evidence_quotes_empty_rules_no_op() -> None:
    """Empty rules_triggered → function returns immediately, no DB call."""
    db = AsyncMock()
    await _fill_evidence_quotes([], uuid.uuid4(), db)
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_fill_evidence_quotes_missing_timestamps_set_to_none() -> None:
    """Evidence without start_ms or end_ms → server_extracted_quote = None."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=mock_result)

    rules = [
        {"rule_id": "R1", "evidence": {}},  # no start_ms / end_ms
    ]
    await _fill_evidence_quotes(rules, uuid.uuid4(), db)
    assert rules[0]["evidence"]["server_extracted_quote"] is None


@pytest.mark.asyncio
async def test_fill_evidence_quotes_finds_words_in_span() -> None:
    """Words within the evidence span are joined and set as server_extracted_quote."""
    word1 = MagicMock()
    word1.word = "I"
    word1.start_ms = 1000

    word2 = MagicMock()
    word2.word = "built"
    word2.start_ms = 1300

    word3 = MagicMock()
    word3.word = "Redis"
    word3.start_ms = 1600

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [word1, word2, word3]
    db.execute = AsyncMock(return_value=mock_result)

    rules = [
        {"rule_id": "R1", "evidence": {"start_ms": 900, "end_ms": 1800}},
    ]
    await _fill_evidence_quotes(rules, uuid.uuid4(), db)
    assert rules[0]["evidence"]["server_extracted_quote"] == "I built Redis"


@pytest.mark.asyncio
async def test_fill_evidence_quotes_no_words_in_span_returns_none() -> None:
    """No words within evidence span → server_extracted_quote = None."""
    word1 = MagicMock()
    word1.word = "unrelated"
    word1.start_ms = 5000  # far outside the span

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [word1]
    db.execute = AsyncMock(return_value=mock_result)

    rules = [
        {"rule_id": "R1", "evidence": {"start_ms": 100, "end_ms": 500}},
    ]
    await _fill_evidence_quotes(rules, uuid.uuid4(), db)
    assert rules[0]["evidence"]["server_extracted_quote"] is None


# ── Scorer: retry logic + ideal diff stub ─────────────────────────────────────


def _make_scorer() -> Scorer:
    """Create a Scorer with mocked Anthropic client."""
    with patch("app.services.scoring.scorer.AsyncAnthropic"):
        return Scorer(api_key="ant-key", quality_profile="balanced")


def _make_valid_result(*, include_ideal: bool = True) -> dict:
    """Build a valid scoring result dict for mock responses."""
    diff = {
        "minimal": {"text": "minimal answer", "changes": [], "estimated_new_score": 65},
        "medium": {"text": "medium answer", "changes": [], "estimated_new_score": 75},
    }
    if include_ideal:
        diff["ideal"] = {"text": "ideal answer", "changes": [], "estimated_new_score": 90}

    return {
        "overall_score": 70,
        "categories": {"technical": 70, "communication": 65},
        "level_assessment": {"assessed_level": "mid", "target_level": "mid", "note": "ok"},
        "rules_triggered": [],
        "diff_versions": diff,
        "memory_hints": {"skill_signals": []},
        "fix_suggestions": [],
        "answer_gaps": [],
        "suggested_answer": "",
    }


@pytest.mark.asyncio
async def test_scorer_ideal_diff_missing_gets_stubbed() -> None:
    """When ideal diff is absent, scorer stubs it from medium and logs a warning."""
    result_without_ideal = _make_valid_result(include_ideal=False)
    mock_metrics = {"input_tokens": 10, "output_tokens": 20, "cached_tokens": 0}

    scorer = _make_scorer()
    with patch.object(
        scorer,
        "_call_anthropic",
        new=AsyncMock(return_value=(result_without_ideal, mock_metrics)),
    ):
        result, _metrics = await scorer._call_with_retry("test prompt")

    # ideal should be stubbed from medium
    assert result["diff_versions"]["ideal"]["text"] == "medium answer"


@pytest.mark.asyncio
async def test_scorer_max_retries_exceeded_raises_runtime_error() -> None:
    """If all retries fail with ValueError, RuntimeError is raised."""
    scorer = _make_scorer()

    with patch.object(
        scorer,
        "_call_anthropic",
        new=AsyncMock(side_effect=ValueError("missing diff_versions")),
    ):
        with pytest.raises(RuntimeError, match="Scoring failed after"):
            await scorer._call_with_retry("test prompt")


# ── DeepgramSTTProvider: init + failed connection ─────────────────────────────


def test_deepgram_stt_init_stores_api_key() -> None:
    """__init__ stores the API key and exposes confidence threshold."""
    from app.services.voice.providers.deepgram_stt import DeepgramSTTProvider

    provider = DeepgramSTTProvider(api_key="dg-test-key")
    assert provider._api_key == "dg-test-key"
    assert provider.STT_CONFIDENCE_THRESHOLD == 0.60


@pytest.mark.asyncio
async def test_deepgram_stt_failed_connection_raises() -> None:
    """transcribe_stream raises RuntimeError when Deepgram connection fails."""
    from app.services.voice.providers.deepgram_stt import DeepgramSTTProvider

    mock_conn = AsyncMock()
    mock_conn.start = AsyncMock(return_value=False)  # connection failed
    mock_conn.on = MagicMock()

    mock_dg_client = MagicMock()
    mock_dg_client.listen.asynclive.v.return_value = mock_conn

    async def empty_audio():
        return
        yield b""  # make it an async generator

    with patch(
        "app.services.voice.providers.deepgram_stt.DeepgramClient",
        return_value=mock_dg_client,
    ):
        provider = DeepgramSTTProvider(api_key="bad-key")
        with pytest.raises(RuntimeError, match="Failed to connect"):
            async for _ in provider.transcribe_stream(empty_audio()):
                pass
