"""Usage logging helper — every API call cost goes to usage_logs.

DoD item 5: Cost displayed in UI, matches profile.
DoD item 6: Cache hit rate > 70% (tracked via cached=True).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_log import UsageLog

logger = structlog.get_logger(__name__)


async def log_usage(
    db: AsyncSession,
    provider: str,
    operation: str,
    cost_usd: Decimal,
    latency_ms: int,
    session_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    cached_tokens: int | None = None,
    audio_seconds: float | None = None,
    characters: int | None = None,
    quality_profile: str | None = None,
    cached: bool = False,
) -> None:
    """Persist one API usage event to usage_logs (non-blocking, fire-and-forget style).

    Never log PII or transcript content — only cost, latency, token counts.
    """
    entry = UsageLog(
        session_id=session_id,
        user_id=user_id,
        provider=provider,
        operation=operation,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        audio_seconds=audio_seconds,
        characters=characters,
        quality_profile=quality_profile,
        cached=cached,
    )
    db.add(entry)
    # Caller is responsible for commit — batch with other writes when possible
    logger.debug(
        "usage.logged",
        provider=provider,
        operation=operation,
        cost_usd=str(cost_usd),
        cached=cached,
    )
