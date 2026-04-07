"""OpenAI GPT LLM provider — streaming text + structured JSON via function calling.

Implements the LLMProvider ABC so it can slot into ProviderSet transparently.
Activated when a user supplies an OpenAI BYOK key in Settings.

Model routing:
  quality/balanced profile → gpt-4o
  budget profile           → gpt-4o-mini
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator
from typing import Any

import structlog
from openai import AsyncOpenAI

from app.services.voice.interfaces import LLMProvider
from app.services.voice.types import LLMMetrics

logger = structlog.get_logger(__name__)

_GPT4O = "gpt-4o"
_GPT4O_MINI = "gpt-4o-mini"


class OpenAILLMProvider(LLMProvider):
    """OpenAI GPT via the official async SDK.

    Streaming: generate_stream() yields str chunks; call get_last_metrics()
    after the generator is exhausted to retrieve token counts + TTFT.

    Structured: generate_json() uses function calling for reliable JSON output
    (mirrors the Anthropic tool_use pattern used by ClaudeLLMProvider).
    """

    def __init__(self, api_key: str, model: str = _GPT4O) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._last_metrics: LLMMetrics | None = None

    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str]:
        """Yield text tokens as they stream from OpenAI.

        Captures TTFT and full usage (prompt_tokens, completion_tokens).
        OpenAI stream_options include_usage delivers usage in the final chunk.
        """
        start = time.monotonic()
        ttft_ms: int | None = None
        self._last_metrics = None

        openai_messages: list[dict[str, str]] = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend(messages)

        input_tokens = 0
        output_tokens = 0

        stream = await self._client.chat.completions.create(  # type: ignore[call-overload]
            model=self.model,
            max_tokens=max_tokens,
            messages=openai_messages,
            stream=True,
            stream_options={"include_usage": True},
        )

        async for chunk in stream:
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens
            if chunk.choices:
                delta = chunk.choices[0].delta.content
                if delta:
                    if ttft_ms is None:
                        ttft_ms = int((time.monotonic() - start) * 1000)
                        logger.debug("openai_llm.ttft", ttft_ms=ttft_ms, model=self.model)
                    yield delta

        self._last_metrics = LLMMetrics(
            ttft_ms=ttft_ms or 0,
            total_latency_ms=int((time.monotonic() - start) * 1000),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=0,
        )

        logger.debug(
            "openai_llm.stream_complete",
            model=self.model,
            ttft_ms=self._last_metrics.ttft_ms,
            input_tokens=self._last_metrics.input_tokens,
            output_tokens=self._last_metrics.output_tokens,
        )

    async def generate_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> tuple[dict[str, Any], LLMMetrics]:
        """Return structured JSON using OpenAI function calling.

        Mirrors the Anthropic tool_use pattern: pass a JSON schema,
        force the model to call the function, parse arguments.
        Raises ValueError if no function call is returned.
        """
        start = time.monotonic()

        openai_messages: list[dict[str, str]] = []
        if system:
            openai_messages.append({"role": "system", "content": system})
        openai_messages.extend(messages)

        response = await self._client.chat.completions.create(  # type: ignore[call-overload]
            model=self.model,
            max_tokens=max_tokens,
            messages=openai_messages,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "structured_output",
                        "description": "Return the required structured output",
                        "parameters": schema,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": "structured_output"}},
        )

        usage = response.usage
        metrics = LLMMetrics(
            ttft_ms=0,
            total_latency_ms=int((time.monotonic() - start) * 1000),
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            cached_tokens=0,
        )

        choice = response.choices[0]
        if choice.message.tool_calls:
            tool_call = choice.message.tool_calls[0]
            result: dict[str, Any] = json.loads(tool_call.function.arguments)
            logger.debug(
                "openai_llm.json_complete",
                model=self.model,
                latency_ms=metrics.total_latency_ms,
            )
            return result, metrics

        raise ValueError(
            f"OpenAI returned no tool_call — model={self.model}, "
            f"finish_reason={choice.finish_reason}"
        )

    def get_last_metrics(self) -> LLMMetrics | None:
        """Return metrics from the most recent generate_stream call."""
        return self._last_metrics
