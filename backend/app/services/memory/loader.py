"""MemoryLoader — load and format user memory for system prompt injection.

Called when a new voice session starts. Returns a formatted text block
that gets appended to the system prompt below the cache boundary.
"""

from __future__ import annotations

import random
import uuid
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_session import InterviewSession
from app.models.skill_graph_node import SkillGraphNode
from app.models.user import User
from app.models.user_memory import UserMemory

logger = structlog.get_logger(__name__)

# Redis cache TTL: 5 minutes +/- 10% jitter (prevents thundering herd)
_CACHE_TTL_BASE = 300
_CACHE_TTL_JITTER = 30


async def load_memory_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    api_key: str | None = None,
) -> str | None:
    """Load user memory and format as a system prompt block.

    Returns None if no memory exists (first-time user).
    Checks Redis cache first; falls back to DB. Caches result for 5 minutes.
    If api_key is provided, checks for a pending Batch API consolidation job.
    """
    cache_key = f"memory:{user_id}"
    redis = None

    # ── 1. Check Redis cache ──────────────────────────────────────────────
    try:
        from app.redis_client import get_redis

        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached is not None:
            logger.debug("memory.cache_hit", user_id=str(user_id))
            return cached if cached != "__NONE__" else None
    except Exception as exc:
        logger.warning("memory.cache_read_failed", error=str(exc))

    # ── 2. Load from DB ───────────────────────────────────────────────────
    result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
    memory = result.scalar_one_or_none()

    if memory is None or not memory.memory_document:
        _cache_miss(redis, cache_key)
        return None

    # ── 2b. Apply pending Batch API consolidation if ready ────────────────
    if api_key and memory.batch_job_id:
        try:
            from app.services.memory.builder import apply_consolidation_batch

            applied = await apply_consolidation_batch(db, user_id, api_key)
            if applied:
                # Re-load after consolidation
                result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
                memory = result.scalar_one_or_none()
                if memory is None or not memory.memory_document:
                    _cache_miss(redis, cache_key)
                    return None
        except Exception as exc:
            logger.warning("memory.consolidation_check_failed", error=str(exc))

    # Guard: memory may have been re-assigned to None inside the consolidation try-block
    if memory is None or not memory.memory_document:
        _cache_miss(redis, cache_key)
        return None

    doc = dict(memory.memory_document)

    # ── 3. Bootstrap from skill_graph if LLM-built memory not yet ready ──
    if not doc.get("weakest_skills") and not doc.get("recurring_mistakes"):
        doc = await _bootstrap_from_skills(db, user_id, doc)

    # ── 4. Format into prompt block ───────────────────────────────────────
    block = _format_memory_block(doc)

    if not block:
        _cache_miss(redis, cache_key)
        return None

    # ── 5. Token budget enforcement (hard cap ~3000 tokens / 12000 chars) ─
    if len(block) > 12000:
        block = block[:12000]

    # ── 6. Cache in Redis ─────────────────────────────────────────────────
    if redis is not None:
        try:
            ttl = _CACHE_TTL_BASE + random.randint(-_CACHE_TTL_JITTER, _CACHE_TTL_JITTER)
            await redis.setex(cache_key, ttl, block)
        except Exception as exc:
            logger.warning("memory.cache_write_failed", error=str(exc))

    return block


def _cache_miss(redis: object | None, cache_key: str) -> None:
    """Cache a miss sentinel so we don't hit DB on every session for new users."""
    import asyncio

    if redis is None:
        return

    async def _set() -> None:
        try:
            ttl = _CACHE_TTL_BASE + random.randint(-_CACHE_TTL_JITTER, _CACHE_TTL_JITTER)
            await redis.setex(cache_key, ttl, "__NONE__")  # type: ignore[attr-defined]
        except Exception as exc:
            logger.warning("memory.cache_miss_redis_error", cache_key=cache_key, error=str(exc))

    try:
        loop = asyncio.get_running_loop()
        asyncio.ensure_future(_set(), loop=loop)
    except RuntimeError as exc:
        logger.warning("memory.cache_miss_event_loop_error", cache_key=cache_key, error=str(exc))


async def _bootstrap_from_skills(
    db: AsyncSession,
    user_id: uuid.UUID,
    doc: dict[str, Any],
) -> dict[str, Any]:
    """Bootstrap memory document from existing skill_graph data.

    Used before the MemoryBuilder has run. Provides immediate value by
    surfacing weakest/strongest skills from the existing skill graph.
    Also enriches with avg_score and goal context from stored profile
    data so bootstrapped docs reach parity with LLM-built ones.
    """
    skills_result = await db.execute(
        select(SkillGraphNode)
        .where(SkillGraphNode.user_id == user_id)
        .order_by(SkillGraphNode.current_score)
    )
    all_skills = skills_result.scalars().all()

    if not all_skills:
        return doc

    doc = dict(doc)
    weakest = all_skills[:4]
    strongest = sorted(all_skills, key=lambda s: s.current_score, reverse=True)[:4]

    doc["weakest_skills"] = [
        {
            "skill": s.skill_name,
            "score": s.current_score,
            "trend": s.trend,
            "top_mistake": (s.typical_mistakes[0] if s.typical_mistakes else None),
            "sessions_practiced": len(s.evidence_links) if s.evidence_links else 0,
        }
        for s in weakest
    ]
    doc["strongest_skills"] = [
        {
            "skill": s.skill_name,
            "score": s.current_score,
            "trend": s.trend,
            "top_mistake": None,
            "sessions_practiced": len(s.evidence_links) if s.evidence_links else 0,
        }
        for s in strongest
    ]

    count_result = await db.execute(
        select(func.count(InterviewSession.id))
        .where(InterviewSession.user_id == user_id)
        .where(InterviewSession.status == "completed")
    )
    doc["total_sessions"] = count_result.scalar() or 0
    doc["avg_score"] = int(sum(s.current_score for s in all_skills) / len(all_skills))

    if not doc.get("target_role") and not doc.get("target_level"):
        user_result = await db.execute(select(User).where(User.id == user_id))
        user_row = user_result.scalar_one_or_none()
        if user_row and user_row.profile:
            profile = user_row.profile
            parsed = profile.get("resume") or {}
            sa = profile.get("self_assessment") or {}
            if not doc.get("target_role"):
                doc["target_role"] = parsed.get("target_role") or sa.get("target_role")
            if not doc.get("target_level"):
                doc["target_level"] = parsed.get("target_level") or sa.get("target_level")
            if not doc.get("career_goal"):
                doc["career_goal"] = parsed.get("career_goal")

    return doc


def _format_memory_block(doc: dict[str, Any]) -> str:
    """Format memory document into the system prompt injection block.

    Uses numbered lists and explicit section counts so the LLM can
    accurately reference quantities without conflating sections.
    """
    total = doc.get("total_sessions", 0)
    if total == 0:
        return ""

    lines: list[str] = [
        "MEMORY CONTEXT -- RETURNING CANDIDATE:",
        f"You have coached this candidate across {total} previous sessions. Use the following context",
        "to personalize your questions and coaching. This context is a summary -- it may be",
        "slightly outdated or incomplete. Prioritize what you observe in THIS session over",
        "stored memory if they conflict.",
        "",
    ]

    career_lines: list[str] = []
    if doc.get("target_role") or doc.get("target_level"):
        parts = [p for p in [doc.get("target_role"), doc.get("target_level")] if p]
        career_lines.append(f"- Target role: {', '.join(parts)}")
    if doc.get("target_companies"):
        career_lines.append(f"- Target companies: {', '.join(doc['target_companies'])}")
    if doc.get("career_goal"):
        career_lines.append(f"- Goal: {doc['career_goal']}")
    if career_lines:
        lines.append("Career:")
        lines.extend(career_lines)
        lines.append("")

    weakest = doc.get("weakest_skills", [])
    if weakest:
        lines.append(f"Weakest areas (focus your probing here) [{len(weakest)} tracked]:")
        for i, s in enumerate(weakest, 1):
            lines.append(f"{i}. {s['skill']} ({s['score']}, {s['trend']})")
        lines.append("")

    skill_mistakes = [(s["skill"], s["top_mistake"]) for s in weakest if s.get("top_mistake")]
    if skill_mistakes:
        lines.append(f"Common mistakes by skill [{len(skill_mistakes)} noted, from skill history]:")
        for skill, mistake in skill_mistakes:
            lines.append(f"- {skill}: {mistake}")
        lines.append("")

    strongest = doc.get("strongest_skills", [])
    if strongest:
        lines.append(f"Strongest areas [{len(strongest)} tracked]:")
        for i, s in enumerate(strongest, 1):
            lines.append(f"{i}. {s['skill']} ({s['score']}, {s['trend']})")
        lines.append("")

    mistakes = doc.get("recurring_mistakes", [])
    if mistakes:
        lines.append(f"Recurring session mistakes [{len(mistakes)} recorded, most recent last]:")
        for i, m in enumerate(mistakes, 1):
            lines.append(f"{i}. {m}")
        lines.append("")

    stories = doc.get("best_stories", [])
    if stories:
        lines.append(f"Best stories (reference naturally if relevant) [{len(stories)} total]:")
        for i, s in enumerate(stories, 1):
            comps = ", ".join(s.get("competencies", []))
            tip = f" -- Tip: {s['tip']}" if s.get("tip") else ""
            lines.append(f'{i}. "{s["title"]}" (score {s.get("best_score", 0)}) -- {comps}{tip}')
        lines.append("")

    comm = doc.get("communication_notes", [])
    if comm:
        lines.append(f"Communication patterns [{len(comm)} observed]:")
        for i, note in enumerate(comm, 1):
            lines.append(f"{i}. {note}")
        lines.append("")

    coaching = doc.get("coaching_insights", [])
    if coaching:
        lines.append(f"Coaching notes [{len(coaching)} recorded]:")
        for i, ci in enumerate(coaching, 1):
            if isinstance(ci, dict):
                count = ci.get("evidence_count", 1)
                insight = ci.get("insight", "")
                lines.append(f"{i}. [observed {count}x] {insight}")
            else:
                lines.append(f"{i}. {ci}")
        lines.append("")

    focus = doc.get("current_focus")
    if focus:
        lines.append(f"Current focus: {focus}")
        lines.append("")

    avg = doc.get("avg_score")
    if avg is not None:
        lines.append(f"Session stats: {total} sessions completed, average score {avg}")

    return "\n".join(lines)

