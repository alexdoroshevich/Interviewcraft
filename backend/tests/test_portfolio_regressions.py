"""Portfolio-readiness regressions. All providers are fake; no API keys/network."""

import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.scoring.scorer import _SCORING_SCHEMA, Scorer
from app.services.voice.costs import calc_anthropic_cost
from app.services.voice.pipeline import VoicePipeline
from app.services.voice.provider_factory import ProviderFactory
from app.services.voice.providers.claude_llm import ClaudeLLMProvider


def test_cache_reads_are_additional_to_ordinary_input():
    assert calc_anthropic_cost("claude-sonnet-4-6", 0, 0, 1000) == Decimal("0.0003")
    assert calc_anthropic_cost("claude-sonnet-4-6", 10, 20, 1000) == Decimal("0.00063")


def test_cache_writes_are_billed_separately_at_the_configured_five_minute_rate():
    assert calc_anthropic_cost(
        "claude-sonnet-4-6", 10, 20, 1000, cache_creation_tokens=200
    ) == Decimal("0.00138")
    assert calc_anthropic_cost("claude-sonnet-4-6", 0, 0, cache_creation_tokens=1000000) == Decimal(
        "3.75"
    )
    assert calc_anthropic_cost("claude-sonnet-4-6", 0, 0) == 0


@pytest.mark.parametrize("counts", [(-1, 0, 0, 0), (0, -1, 0, 0), (0, 0, -1, 0), (0, 0, 0, -1)])
def test_negative_usage_counts_are_rejected(counts):
    with pytest.raises(ValueError, match="non-negative"):
        calc_anthropic_cost("claude-sonnet-4-6", *counts)


class FakeTTS:
    def __init__(self, api_key="", fail=False, **kwargs):
        self.key = api_key
        self.fail = fail
        self.calls = 0

    async def synthesize_stream(self, text):
        self.calls += 1
        if self.fail:
            raise RuntimeError("synthetic provider failure")
        yield b"synthetic audio"


def providers(profile, byok):
    settings = SimpleNamespace(
        deepgram_api_key="platform-dg",
        anthropic_api_key="platform-ant",
        elevenlabs_api_key="platform-el",
    )
    with (
        patch("app.services.voice.provider_factory.DeepgramSTTProvider") as stt,
        patch("app.services.voice.provider_factory.DeepgramTTSProvider", side_effect=FakeTTS),
        patch(
            "app.services.voice.provider_factory.ElevenLabsTTSProvider",
            return_value=FakeTTS(fail=True),
        ),
        patch(
            "app.services.voice.provider_factory.ClaudeLLMProvider",
            return_value=MagicMock(model="fake"),
        ),
    ):
        result = ProviderFactory.create(profile, settings, byok_keys=byok)
    return result, stt


@pytest.mark.parametrize("profile", ["quality", "balanced", "budget"])
@pytest.mark.parametrize("byok", [{}, {"deepgram": "user-dg"}])
def test_deepgram_stt_budget_tts_and_fallback_share_the_resolved_key(profile, byok):
    result, stt = providers(profile, byok)
    expected = byok.get("deepgram", "platform-dg")
    stt.assert_called_once_with(api_key=expected)
    selected = result.tts if profile == "budget" else getattr(result, "fallback_tts", None)
    assert selected is not None
    assert selected.key == expected
    if profile == "budget":
        assert result.fallback_tts is None


@pytest.mark.asyncio
async def test_fallback_uses_the_session_provider_without_reloading_platform_settings():
    result, _ = providers("balanced", {"deepgram": "user-dg"})
    pipeline = VoicePipeline.__new__(VoicePipeline)
    pipeline._providers = result
    pipeline._tts_fallback_active = False
    pipeline._tts_fallback_reason = ""
    with patch(
        "app.config.Settings", side_effect=AssertionError("No settings reload during fallback")
    ):
        chunks = [chunk async for chunk in pipeline._synthesize_with_fallback("hello")]
    assert chunks == [b"synthetic audio"]
    assert result.tts.key == "user-dg"
    assert pipeline._tts_fallback_active
    result.tts.fail = True
    with patch("app.config.Settings", side_effect=AssertionError("No billing-owner switch")):
        with pytest.raises(RuntimeError, match="synthetic provider failure"):
            _ = [chunk async for chunk in pipeline._synthesize_with_fallback("again")]


@pytest.mark.asyncio
async def test_budget_deepgram_failure_does_not_retry_with_a_platform_key():
    result, _ = providers("budget", {"deepgram": "invalid-user-key"})
    result.tts.fail = True
    pipeline = VoicePipeline.__new__(VoicePipeline)
    pipeline._providers = result
    pipeline._tts_fallback_active = False
    pipeline._tts_fallback_reason = ""
    with patch("app.config.Settings", side_effect=AssertionError("No platform key fallback")):
        with pytest.raises(RuntimeError, match="synthetic provider failure"):
            _ = [chunk async for chunk in pipeline._synthesize_with_fallback("hello")]
    assert result.tts.calls == 1


def test_every_local_scoring_schema_reference_resolves_from_its_root():
    references = []

    def visit(value):
        if isinstance(value, dict):
            if "$ref" in value:
                references.append(value["$ref"])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(_SCORING_SCHEMA)
    assert len(references) == 3
    for reference in references:
        assert reference.startswith("#/")
        resolved = _SCORING_SCHEMA
        for part in reference[2:].split("/"):
            resolved = resolved[part.replace("~1", "/").replace("~0", "~")]
        assert set(resolved["required"]) == {"text", "changes", "estimated_new_score"}


@pytest.mark.asyncio
async def test_structured_provider_and_scorer_capture_cache_creation_usage():
    usage = SimpleNamespace(
        input_tokens=10,
        output_tokens=20,
        cache_read_input_tokens=1000,
        cache_creation_input_tokens=200,
    )
    response = SimpleNamespace(
        usage=usage,
        content=[SimpleNamespace(type="tool_use", name="structured_output", input={"ok": True})],
    )
    client = MagicMock()
    client.messages.create = AsyncMock(return_value=response)
    with patch("app.services.voice.providers.claude_llm.AsyncAnthropic", return_value=client):
        provider = ClaudeLLMProvider(api_key="fake")
        _, metrics = await provider.generate_json([], {"type": "object"})
    assert metrics.cached_tokens == 1000
    assert metrics.cache_creation_tokens == 200
    with patch("app.services.scoring.scorer.AsyncAnthropic", return_value=client):
        scorer = Scorer(api_key="fake")
        _, scoring_metrics = await scorer._call_anthropic("synthetic transcript", 0)
    assert scoring_metrics["cache_creation_tokens"] == 200


@pytest.mark.asyncio
async def test_interrupt_cancels_and_awaits_the_sentence_tts_worker():
    from app.services.voice.types import LatencySnapshot

    started = asyncio.Event()
    stopped = asyncio.Event()
    never = asyncio.Event()
    existing_tasks = set(asyncio.all_tasks())

    async def tokens(**kwargs):
        yield "Hello. "
        await never.wait()

    async def audio(text):
        started.set()
        try:
            await never.wait()
            yield b"unreachable"
        finally:
            stopped.set()

    provider_set, _ = providers("balanced", {})
    provider_set.voice_llm.generate_stream = tokens
    session = SimpleNamespace(type="behavioral", persona="neutral", company=None, focus_skill=None)
    pipeline = VoicePipeline(provider_set, AsyncMock(), session, MagicMock())
    pipeline._synthesize_with_fallback = audio
    task = asyncio.create_task(pipeline._llm_tts_turn(AsyncMock(), LatencySnapshot()))
    await asyncio.wait_for(started.wait(), timeout=1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    try:
        await asyncio.wait_for(stopped.wait(), timeout=0.1)
    finally:
        leaked = set(asyncio.all_tasks()) - existing_tasks
        for pending in leaked:
            pending.cancel()
        await asyncio.gather(*leaked, return_exceptions=True)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "cached, expected", [(b"saved memory", "saved memory"), (b"__NONE__", None)]
)
async def test_memory_cache_bytes_are_normalized_before_the_prompt(cached, expected):
    from app.services.memory.loader import load_memory_context

    redis = AsyncMock()
    redis.get.return_value = cached
    db = AsyncMock()
    with patch("app.redis_client.get_redis", new=AsyncMock(return_value=redis)):
        result = await load_memory_context(db, MagicMock())
    assert result == expected
    db.execute.assert_not_awaited()
