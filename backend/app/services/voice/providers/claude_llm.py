"""Claude LLM provider — streaming text + structured JSON via tool_use.

Scoring is calibrated to Claude Sonnet (see HANDOFF.md).
WARN at startup if a non-Sonnet model is used for voice_llm.

Per-task model routing is enforced by ProviderSet — this class does NOT
decide which model to use; it receives the model name from ProviderFactory.
"""

from __future__ import annotations

import time
from collections.abc import AsyncGenerator
from typing import Any, cast

import structlog
from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from app.services.voice.interfaces import LLMProvider
from app.services.voice.types import LLMMetrics

logger = structlog.get_logger(__name__)

_SONNET = "claude-sonnet-4-6"
_HAIKU = "claude-haiku-4-5-20251001"


class ClaudeLLMProvider(LLMProvider):
    """Anthropic Claude via the official async SDK.

    Streaming: generate_stream() yields str chunks; call get_last_metrics()
    after the generator is exhausted to retrieve token counts + TTFT.

    Structured: generate_json() uses tool_use for reliable JSON output
    (avoids fragile text-mode JSON parsing).
    """

    def __init__(self, api_key: str, model: str = _SONNET) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self.model = model
        self._last_metrics: LLMMetrics | None = None

        if model not in (_SONNET, _HAIKU):
            logger.warning(
                "claude_llm.non_standard_model",
                model=model,
                note="Scoring is calibrated to claude-sonnet-4-6; variance may increase",
            )

    async def generate_stream(  # type: ignore[override]
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str]:
        """Yield text tokens as they stream from Claude.

        Captures TTFT (time to first token) and full usage after stream ends.
        """
        start = time.monotonic()
        ttft_ms: int | None = None
        self._last_metrics = None

        async with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            messages=cast(list[MessageParam], messages),
            system=system or "",
        ) as stream:
            async for text in stream.text_stream:
                if ttft_ms is None:
                    ttft_ms = int((time.monotonic() - start) * 1000)
                    logger.debug("claude_llm.ttft", ttft_ms=ttft_ms, model=self.model)
                yield text

            final_msg = await stream.get_final_message()
            usage = final_msg.usage
            self._last_metrics = LLMMetrics(
                ttft_ms=ttft_ms or 0,
                total_latency_ms=int((time.monotonic() - start) * 1000),
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                cached_tokens=getattr(usage, "cache_read_input_tokens", 0),
            )

        logger.debug(
            "claude_llm.stream_complete",
            model=self.model,
            ttft_ms=self._last_metrics.ttft_ms,
            input_tokens=self._last_metrics.input_tokens,
            output_tokens=self._last_metrics.output_tokens,
            cached_tokens=self._last_metrics.cached_tokens,
        )

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> tuple[dict[str, Any], LLMMetrics]:
        """Return structured JSON using Anthropic tool_use (reliable, no regex parsing).

        Used for the single-batched score+diff+memory call (Weeks 3-4).
        Raises ValueError if no tool_use block is returned.
        """
        start = time.monotonic()

        response = await self._client.messages.create(  # type: ignore[call-overload]
            model=self.model,
            max_tokens=max_tokens,
            messages=cast(list[MessageParam], messages),
            system=system or "",
            tools=[
                {
                    "name": "structured_output",
                    "description": "Return the required structured output",
                    "input_schema": schema,
                }
            ],
            tool_choice={"type": "tool", "name": "structured_output"},
        )

        usage = response.usage
        metrics = LLMMetrics(
            ttft_ms=0,  # Not applicable for non-streaming
            total_latency_ms=int((time.monotonic() - start) * 1000),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=getattr(usage, "cache_read_input_tokens", 0),
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "structured_output":
                logger.debug(
                    "claude_llm.json_complete",
                    model=self.model,
                    latency_ms=metrics.total_latency_ms,
                )
                return cast(dict[str, Any], block.input), metrics

        raise ValueError(
            f"Claude returned no tool_use block — model={self.model}, "
            f"stop_reason={response.stop_reason}"
        )

    def get_last_metrics(self) -> LLMMetrics | None:
        """Return metrics from the most recent generate_stream call."""
        return self._last_metrics
