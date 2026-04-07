"""Session report PDF generator via Anthropic Skills API (beta).

Uses the built-in 'pdf' skill to generate a professional coaching report.
File IDs are cached in Redis for 24 hours to avoid regeneration costs.

Skills API betas required:
  - code-execution-2025-08-25
  - files-api-2025-04-14
  - skills-2025-10-02
"""

from __future__ import annotations

import time
import uuid
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_session import InterviewSession
from app.models.segment_score import SegmentScore
from app.models.usage_log import UsageLog

logger = structlog.get_logger(__name__)

_REPORT_MODEL = "claude-sonnet-4-6"
_CACHE_TTL_SECONDS = 86400  # 24 hours

_REPORT_PROMPT = """\
Generate a professional interview coaching report as a well-structured PDF document.

Session overview:
- Session type: {session_type}
- Company: {company}
- Persona: {persona}
- Total questions: {total_segments}
- Overall average score: {avg_score}/10
- Session date: {session_date}

Per-question breakdown:
{segments_text}

Instructions for the PDF report:
1. Title: "InterviewCraft Coaching Report"
2. Executive summary: 2-3 sentences on overall performance
3. Strengths section: what the candidate did well (from high scores + positive rules)
4. Growth areas section: top 3 mistakes to address (from rules_triggered)
5. Per-question details: question, score, key feedback points, recommended improvement
6. Next steps: 3 actionable coaching recommendations

Make the report professional, encouraging, and actionable. Use clear headings and bullet points.
"""


async def generate_session_pdf(
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    api_key: str,
    db: AsyncSession,
) -> str:
    """Generate a PDF coaching report for a scored session.

    Returns a file_id (expires 24h) cached in Redis.
    Raises ValueError if session is not completed/scored.
    """
    cache_key = f"report:file_id:{session_id}"

    # ── 1. Check Redis cache ──────────────────────────────────────────────────
    redis = None
    try:
        from app.redis_client import get_redis

        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            logger.debug("report.cache_hit", session_id=str(session_id))
            return str(cached)
    except Exception as exc:
        logger.warning("report.cache_read_failed", error=str(exc))

    # ── 2. Load session + scores ──────────────────────────────────────────────
    sess_result = await db.execute(
        select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        raise ValueError("Session not found.")
    if session.status != "completed":
        raise ValueError("Session is not completed — report unavailable.")

    scores_result = await db.execute(
        select(SegmentScore)
        .where(SegmentScore.session_id == session_id)
        .order_by(SegmentScore.segment_index)
    )
    segments: list[SegmentScore] = list(scores_result.scalars().all())

    if not segments:
        raise ValueError("No scored segments found — report unavailable.")

    # ── 3. Build prompt ───────────────────────────────────────────────────────
    avg_score = round(sum(s.overall_score for s in segments) / len(segments), 1)
    segments_text = _format_segments(segments)
    session_date = session.created_at.strftime("%Y-%m-%d") if session.created_at else "N/A"

    prompt = _REPORT_PROMPT.format(
        session_type=session.type,
        company=session.company or "Not specified",
        persona=session.persona or "Default",
        total_segments=len(segments),
        avg_score=avg_score,
        session_date=session_date,
        segments_text=segments_text,
    )

    # ── 4. Call Skills API ────────────────────────────────────────────────────
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    start_ms = int(time.monotonic() * 1000)

    response = await client.beta.messages.create(
        model=_REPORT_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        betas=[
            "code-execution-2025-08-25",
            "files-api-2025-04-14",
            "skills-2025-10-02",
        ],
        extra_body={
            "container": {"skills": [{"type": "anthropic", "skill_id": "pdf", "version": "latest"}]}
        },
    )

    latency_ms = int(time.monotonic() * 1000) - start_ms

    # ── 5. Extract file_id ────────────────────────────────────────────────────
    file_id = _extract_file_id(response)
    if not file_id:
        raise ValueError("Skills API did not return a file_id — PDF generation failed.")

    logger.info(
        "report.generated",
        session_id=str(session_id),
        file_id=file_id,
        latency_ms=latency_ms,
    )

    # ── 6. Log cost ───────────────────────────────────────────────────────────
    usage = getattr(response, "usage", None)
    input_tokens = getattr(usage, "input_tokens", 0) or 0
    output_tokens = getattr(usage, "output_tokens", 0) or 0
    # Sonnet 4.6: $3/M input, $15/M output
    cost = Decimal(str(input_tokens * 3 / 1_000_000 + output_tokens * 15 / 1_000_000))

    usage_log = UsageLog(
        user_id=user_id,
        session_id=session_id,
        provider="anthropic",
        operation="report_generate",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
        latency_ms=latency_ms,
        cached=False,
    )
    db.add(usage_log)
    await db.commit()

    # ── 7. Cache file_id ──────────────────────────────────────────────────────
    if redis is not None:
        try:
            await redis.setex(cache_key, _CACHE_TTL_SECONDS, file_id)
        except Exception as exc:
            logger.warning("report.cache_write_failed", error=str(exc))

    return file_id


async def download_report_pdf(file_id: str, api_key: str) -> bytes:
    """Download the generated PDF bytes from the Files API."""
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    response = await client.beta.files.content(file_id)  # type: ignore[attr-defined]
    data: bytes = response.read()
    return data


def _format_segments(segments: list[SegmentScore]) -> str:
    """Format segment scores into a compact text block for the prompt."""
    lines: list[str] = []
    for seg in segments:
        lines.append(f"\nQ{seg.segment_index + 1}: {seg.question_text}")
        lines.append(f"Score: {seg.overall_score}/10")
        cats = seg.category_scores or {}
        if cats:
            cat_str = ", ".join(f"{k}: {v}" for k, v in cats.items())
            lines.append(f"Categories: {cat_str}")
        rules = seg.rules_triggered or []
        if rules:
            triggered = [r.get("rule", "") for r in rules[:3]]
            lines.append(f"Key feedback: {'; '.join(triggered)}")
        if seg.diff_versions:
            ideal = seg.diff_versions.get("ideal", {})
            ideal_text = ideal.get("answer", "") if isinstance(ideal, dict) else ""
            if ideal_text:
                lines.append(f"Ideal answer (excerpt): {ideal_text[:200]}...")
    return "\n".join(lines)


def _extract_file_id(response: Any) -> str | None:
    """Extract file_id from Skills API response content blocks."""
    content = getattr(response, "content", [])
    for block in content:
        # Skills API returns tool_result blocks containing file references
        block_type = getattr(block, "type", "")
        if block_type == "tool_result":
            inner = getattr(block, "content", [])
            for item in inner if isinstance(inner, list) else []:
                if getattr(item, "type", "") == "document":
                    fid = getattr(item, "file_id", None) or (getattr(item, "source", {}) or {}).get(
                        "file_id"
                    )
                    if fid:
                        return str(fid)
        # Some SDK versions surface file_id directly on a block
        if hasattr(block, "file_id") and block.file_id:
            return str(block.file_id)
        # Check for nested source dict
        source = getattr(block, "source", None)
        if isinstance(source, dict) and source.get("file_id"):
            return str(source["file_id"])
    return None
