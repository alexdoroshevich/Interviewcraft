"""MemoryBuilder — extract memory updates from a completed session.

Triggered when session status transitions to "completed".
Uses Haiku for extraction (~$0.002/call).
Write discipline: only update user_memories after confirmed DB write.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interview_session import InterviewSession
from app.models.segment_score import SegmentScore
from app.models.skill_graph_node import SkillGraphNode
from app.models.story import Story
from app.models.user_memory import UserMemory
from app.services.usage import log_usage
from app.services.voice.costs import calc_anthropic_cost

logger = structlog.get_logger(__name__)

_HAIKU = "claude-haiku-4-5"
_MAX_RETRIES = 2
_CONSOLIDATION_THRESHOLD = 20  # sessions before triggering Batch API consolidation

_CONSOLIDATION_SYSTEM = (
    "You are a memory consolidation system for an interview coaching platform. "
    "Given a candidate's accumulated memory document, produce a clean, de-duplicated, "
    "prioritized version. Remove stale or contradictory observations. Keep the most "
    "evidence-backed mistakes and coaching insights. Preserve all career context and "
    "best stories. Output ONLY a valid JSON object matching the input structure."
)


_EXTRACTION_TOOL: dict[str, Any] = {
    "name": "update_memory",
    "description": "Extract memory-worthy observations from this interview session",
    "input_schema": {
        "type": "object",
        "required": [
            "recurring_mistakes",
            "story_detected",
            "communication_observations",
            "coaching_observation",
            "focus_suggestion",
        ],
        "properties": {
            "recurring_mistakes": {
                "type": "array",
                "maxItems": 3,
                "items": {"type": "string"},
                "description": (
                    "Specific, actionable mistakes observed in this session. "
                    "Use precise language: 'Forgot to quantify the latency improvement' "
                    "not 'Could improve results section'."
                ),
            },
            "story_detected": {
                "type": "object",
                "properties": {
                    "found": {"type": "boolean"},
                    "title": {"type": ["string", "null"]},
                    "competencies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 3,
                    },
                    "tip": {
                        "type": ["string", "null"],
                        "description": "One concrete tip to improve this story next time",
                    },
                },
            },
            "communication_observations": {
                "type": "array",
                "maxItems": 2,
                "items": {"type": "string"},
                "description": (
                    "Communication style observations: pacing, rambling, filler words, "
                    "confidence, structure. Only include if notably good or bad."
                ),
            },
            "coaching_observation": {
                "type": ["string", "null"],
                "description": (
                    "What coaching approach worked or didn't work in this session. "
                    "Example: 'Direct challenge on metrics led to a much stronger answer on retry'"
                ),
            },
            "focus_suggestion": {
                "type": ["string", "null"],
                "description": (
                    "What this candidate should practice next, based on this session. "
                    "Be specific: 'Practice capacity estimation with storage calculations' "
                    "not 'Work on system design'."
                ),
            },
        },
    },
}

_EXTRACTION_SYSTEM = (
    "You are a memory extraction system for an interview coaching platform. "
    "Given a completed interview session's questions, answers, and scores, "
    "extract observations worth remembering for future sessions. "
    "Be specific and actionable. Do not repeat generic advice. "
    "Only flag patterns that would actually change how a coach approaches this candidate."
)


async def build_memory(
    db: AsyncSession,
    session: InterviewSession,
    user_id: uuid.UUID,
    api_key: str,
) -> bool:
    """Extract memory from a completed session and merge into user_memories.

    Returns True if memory was updated, False on error or no-op.
    """
    # ── 1. Load session segments ──────────────────────────────────────────
    segments_result = await db.execute(
        select(SegmentScore)
        .where(SegmentScore.session_id == session.id)
        .order_by(SegmentScore.segment_index)
    )
    segments = list(segments_result.scalars().all())

    if not segments:
        logger.info("memory.build_skipped_no_segments", session_id=str(session.id))
        return False

    # ── 2. Build extraction prompt ────────────────────────────────────────
    session_summary_lines = [
        f"Session type: {session.type}",
        f"Company: {getattr(session, 'company', None) or 'none'}",
        f"Persona: {getattr(session, 'persona', 'default')}",
        f"Focus skill: {getattr(session, 'focus_skill', None) or 'none'}",
        f"Segments: {len(segments)}",
    ]

    segment_blocks: list[str] = []
    for seg in segments:
        block = (
            f"Q{seg.segment_index + 1}: {seg.question_text}\n"
            f"Score: {seg.overall_score}/100 (confidence: {seg.confidence})\n"
            f"Categories: {json.dumps(seg.category_scores)}\n"
        )
        answer_preview = seg.answer_text[:500]
        if len(seg.answer_text) > 500:
            answer_preview += "..."
        block += f"Answer preview: {answer_preview}\n"
        segment_blocks.append(block)

    user_message = (
        "SESSION SUMMARY:\n"
        + "\n".join(session_summary_lines)
        + "\n\nSEGMENT DETAILS:\n"
        + "\n---\n".join(segment_blocks)
    )

    # ── 3. Call Haiku for extraction ──────────────────────────────────────
    client = AsyncAnthropic(api_key=api_key)
    t0 = time.monotonic()
    retries = 0
    extraction: dict[str, Any] | None = None
    response = None

    while retries <= _MAX_RETRIES:
        try:
            response = await client.messages.create(  # type: ignore[call-overload]
                model=_HAIKU,
                max_tokens=1024,
                system=_EXTRACTION_SYSTEM,
                tools=[_EXTRACTION_TOOL],
                tool_choice={"type": "tool", "name": "update_memory"},
                messages=[{"role": "user", "content": user_message}],
            )
            tool_block = next(
                (b for b in response.content if b.type == "tool_use" and b.name == "update_memory"),
                None,
            )
            if tool_block:
                extraction = tool_block.input
                break
            retries += 1
        except Exception as exc:
            logger.error("memory.extraction_failed", error=str(exc), retry=retries)
            retries += 1

    latency_ms = int((time.monotonic() - t0) * 1000)

    if extraction is None or response is None:
        logger.error("memory.extraction_exhausted", session_id=str(session.id))
        return False

    # ── 4. Log cost ───────────────────────────────────────────────────────
    cost = calc_anthropic_cost(
        _HAIKU,
        response.usage.input_tokens,
        response.usage.output_tokens,
        getattr(response.usage, "cache_read_input_tokens", 0),
    )
    await log_usage(
        db,
        provider="anthropic",
        operation="memory_build",
        cost_usd=cost,
        latency_ms=latency_ms,
        session_id=session.id,
        user_id=user_id,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

    # ── 5. Merge into user_memories (atomic) ──────────────────────────────
    try:
        await _merge_extraction(db, user_id, session, segments, extraction)
        await db.commit()
        logger.info(
            "memory.built",
            session_id=str(session.id),
            user_id=str(user_id),
            cost_usd=str(cost),
            latency_ms=latency_ms,
        )
    except Exception as exc:
        await db.rollback()
        logger.error("memory.merge_failed", error=str(exc), session_id=str(session.id))
        return False

    # ── 6. Invalidate Redis cache ─────────────────────────────────────────
    try:
        from app.redis_client import get_redis

        redis = await get_redis()
        await redis.delete(f"memory:{user_id}")
    except Exception as exc:
        logger.warning("memory.cache_invalidation_failed", error=str(exc))

    # ── 7. Trigger consolidation if threshold reached ─────────────────────
    # Re-load the row to check sessions_since_consolidation after the merge.
    try:
        result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
        memory_row = result.scalar_one_or_none()
        if (
            memory_row is not None
            and memory_row.sessions_since_consolidation >= _CONSOLIDATION_THRESHOLD
            and not memory_row.batch_job_id
        ):
            await consolidate_memory(db, user_id, api_key)
    except Exception as exc:
        logger.warning("memory.consolidation_trigger_failed", error=str(exc))

    return True


async def _merge_extraction(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: InterviewSession,
    segments: list[SegmentScore],
    extraction: dict[str, Any],
) -> None:
    """Merge LLM extraction into the user_memories row.

    Creates the row if it doesn't exist. Uses full JSONB reassignment
    (SQLAlchemy doesn't detect in-place JSONB mutations).
    """
    result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
    memory = result.scalar_one_or_none()

    if memory is None:
        memory = UserMemory(user_id=user_id, memory_document={})
        db.add(memory)

    doc = dict(memory.memory_document or {})

    # ── Recurring mistakes (deduplicate, cap at 6) ──────────────────
    existing_mistakes: list[str] = list(doc.get("recurring_mistakes", []))
    for m in extraction.get("recurring_mistakes", []):
        if m and m not in existing_mistakes:
            existing_mistakes.append(m)
    doc["recurring_mistakes"] = existing_mistakes[-6:]

    # ── Story ───────────────────────────────────────────────────────
    story_data = extraction.get("story_detected", {})
    if story_data.get("found") and story_data.get("title"):
        avg_score = sum(s.overall_score for s in segments) // len(segments) if segments else 0
        # Upsert into stories table so score ranking stays authoritative
        existing_row = await db.execute(
            select(Story).where(
                Story.user_id == user_id,
                Story.title == story_data["title"],
            )
        )
        story_row = existing_row.scalar_one_or_none()
        if story_row is not None:
            story_row.best_score_with_this_story = max(
                story_row.best_score_with_this_story or 0, avg_score
            )
            story_row.times_used += 1
        else:
            story_row = Story(
                user_id=user_id,
                title=story_data["title"],
                summary=story_data.get("tip") or story_data["title"],
                competencies=story_data.get("competencies", []),
                best_score_with_this_story=avg_score,
                times_used=1,
                auto_detected=True,
                source_session_id=session.id,
            )
            db.add(story_row)
        await db.flush()  # ensure row exists before the ranking query

        # Rebuild best_stories from DB — top 4 by best score (score-ranked, not insertion order)
        # Only rebuild when a story was detected; otherwise leave existing list unchanged.
        top_stories_result = await db.execute(
            select(Story)
            .where(Story.user_id == user_id)
            .order_by(Story.best_score_with_this_story.desc().nulls_last())
            .limit(4)
        )
        top_stories = top_stories_result.scalars().all()
        if top_stories:
            doc["best_stories"] = [
                {
                    "title": s.title,
                    "best_score": s.best_score_with_this_story or 0,
                    "competencies": s.competencies,
                    "tip": s.summary if s.summary != s.title else None,
                }
                for s in top_stories
            ]

    # ── Communication notes ─────────────────────────────────────────
    comm_notes: list[str] = extraction.get("communication_observations", [])
    if comm_notes:
        existing_comm: list[str] = list(doc.get("communication_notes", []))
        for note in comm_notes:
            if note and note not in existing_comm:
                existing_comm.append(note)
        doc["communication_notes"] = existing_comm[-3:]

    # ── Coaching insights ───────────────────────────────────────────
    coaching = extraction.get("coaching_observation")
    if coaching:
        existing_coaching: list[dict[str, Any]] = list(doc.get("coaching_insights", []))
        found = False
        for ci in existing_coaching:
            if _similar_insight(ci.get("insight", ""), coaching):
                ci["evidence_count"] = ci.get("evidence_count", 1) + 1
                found = True
                break
        if not found:
            existing_coaching.append({"insight": coaching, "evidence_count": 1})
        doc["coaching_insights"] = existing_coaching[-3:]

    # ── Current focus ───────────────────────────────────────────────
    focus = extraction.get("focus_suggestion")
    if focus:
        doc["current_focus"] = focus

    # ── Skill snapshots from skill_graph ────────────────────────────
    skills_result = await db.execute(
        select(SkillGraphNode)
        .where(SkillGraphNode.user_id == user_id)
        .order_by(SkillGraphNode.current_score)
    )
    all_skills = skills_result.scalars().all()

    if all_skills:
        weakest = all_skills[:4]
        strongest = sorted(all_skills, key=lambda s: s.current_score, reverse=True)[:4]
        doc["weakest_skills"] = [
            {
                "skill": s.skill_name,
                "score": s.current_score,
                "trend": s.trend,
                "top_mistake": (s.typical_mistakes[0] if s.typical_mistakes else None),
                "sessions_practiced": (len(s.evidence_links) if s.evidence_links else 0),
            }
            for s in weakest
        ]
        doc["strongest_skills"] = [
            {
                "skill": s.skill_name,
                "score": s.current_score,
                "trend": s.trend,
                "top_mistake": None,
                "sessions_practiced": (len(s.evidence_links) if s.evidence_links else 0),
            }
            for s in strongest
        ]

    # ── Session stats ───────────────────────────────────────────────
    doc["total_sessions"] = doc.get("total_sessions", 0) + 1
    session_avg = sum(s.overall_score for s in segments) // len(segments) if segments else None
    if session_avg is not None:
        prev_avg = doc.get("avg_score")
        prev_total = doc.get("total_sessions", 1) - 1
        if prev_avg is not None and prev_total > 0:
            doc["avg_score"] = int((prev_avg * prev_total + session_avg) / (prev_total + 1))
        else:
            doc["avg_score"] = session_avg

    # ── Token estimate (1 token ~4 chars) ───────────────────────────
    estimated_tokens = len(json.dumps(doc)) // 4

    # ── Write (full JSONB reassignment — SQLAlchemy requires this) ───
    memory.memory_document = doc
    memory.version = (memory.version or 0) + 1
    memory.token_count = estimated_tokens
    memory.sessions_since_consolidation = (memory.sessions_since_consolidation or 0) + 1
    memory.last_built_at = datetime.now(tz=UTC)
    memory.updated_at = datetime.now(tz=UTC)


async def consolidate_memory(
    db: AsyncSession,
    user_id: uuid.UUID,
    api_key: str,
) -> bool:
    """Submit a Batch API job to consolidate and de-duplicate the memory document.

    Uses the Anthropic Batch API (50% cheaper than synchronous calls).
    Stores the batch_job_id on the user_memories row. Results are applied
    lazily by apply_consolidation_batch() on the next load_memory_context() call.

    Returns True if a batch job was successfully submitted.
    """
    result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
    memory = result.scalar_one_or_none()
    if memory is None or not memory.memory_document:
        return False
    if memory.batch_job_id:
        logger.info(
            "memory.consolidation_already_pending",
            user_id=str(user_id),
            batch_job_id=memory.batch_job_id,
        )
        return False

    doc_json = json.dumps(memory.memory_document, indent=2)
    client = AsyncAnthropic(api_key=api_key)

    try:
        batch = await client.beta.messages.batches.create(
            requests=[
                {
                    "custom_id": f"consolidate-{user_id}",
                    "params": {
                        "model": _HAIKU,
                        "max_tokens": 2048,
                        "system": _CONSOLIDATION_SYSTEM,
                        "messages": [
                            {
                                "role": "user",
                                "content": (
                                    "Consolidate this memory document into a clean, "
                                    "de-duplicated version. Return only the JSON object:\n\n"
                                    f"{doc_json}"
                                ),
                            }
                        ],
                    },
                }
            ]
        )
    except Exception as exc:
        logger.error("memory.batch_submit_failed", error=str(exc), user_id=str(user_id))
        return False

    memory.batch_job_id = batch.id
    await db.commit()

    logger.info(
        "memory.consolidation_submitted",
        user_id=str(user_id),
        batch_id=batch.id,
    )
    return True


async def apply_consolidation_batch(
    db: AsyncSession,
    user_id: uuid.UUID,
    api_key: str,
) -> bool:
    """Check if a pending Batch API consolidation job is complete and apply it.

    Called by load_memory_context() when batch_job_id is set.
    Returns True if the memory was updated.
    """
    result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
    memory = result.scalar_one_or_none()
    if memory is None or not memory.batch_job_id:
        return False

    client = AsyncAnthropic(api_key=api_key)

    try:
        batch = await client.beta.messages.batches.retrieve(memory.batch_job_id)
    except Exception as exc:
        logger.warning(
            "memory.batch_retrieve_failed",
            error=str(exc),
            user_id=str(user_id),
            batch_id=memory.batch_job_id,
        )
        return False

    if batch.processing_status != "ended":
        logger.debug(
            "memory.batch_pending",
            user_id=str(user_id),
            batch_id=memory.batch_job_id,
            status=batch.processing_status,
        )
        return False

    # Batch is done — retrieve results
    try:
        consolidated_doc: dict[str, Any] | None = None
        async for result_item in await client.beta.messages.batches.results(memory.batch_job_id):
            if result_item.custom_id == f"consolidate-{user_id}":
                if result_item.result.type == "succeeded":
                    raw = result_item.result.message.content[0].text  # type: ignore[union-attr]
                    consolidated_doc = json.loads(raw)
                break
    except Exception as exc:
        logger.error(
            "memory.batch_result_failed",
            error=str(exc),
            user_id=str(user_id),
            batch_id=memory.batch_job_id,
        )
        return False

    if consolidated_doc is None:
        logger.warning(
            "memory.batch_no_result",
            user_id=str(user_id),
            batch_id=memory.batch_job_id,
        )
        memory.batch_job_id = None
        await db.commit()
        return False

    estimated_tokens = len(json.dumps(consolidated_doc)) // 4
    memory.memory_document = consolidated_doc
    memory.version = memory.version + 1
    memory.token_count = estimated_tokens
    memory.sessions_since_consolidation = 0
    memory.last_consolidated_at = datetime.now(tz=UTC)
    memory.batch_job_id = None
    memory.updated_at = datetime.now(tz=UTC)

    try:
        await db.commit()
        logger.info(
            "memory.consolidated",
            user_id=str(user_id),
            token_count=estimated_tokens,
        )
        # Invalidate Redis cache
        from app.redis_client import get_redis

        redis = await get_redis()
        await redis.delete(f"memory:{user_id}")
    except Exception as exc:
        await db.rollback()
        logger.error("memory.consolidation_apply_failed", error=str(exc))
        return False

    return True


async def search_stories_fts(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    limit: int = 4,
) -> list[Story]:
    """Find user stories using PostgreSQL FTS, ranked by best score.

    Uses the ix_stories_fts GIN index (migration 018).
    Falls back to score-only ranking when query is empty.
    """
    from sqlalchemy import func as sa_func

    if not query.strip():
        result = await db.execute(
            select(Story)
            .where(Story.user_id == user_id)
            .order_by(Story.best_score_with_this_story.desc().nulls_last())
            .limit(limit)
        )
        return list(result.scalars().all())

    result = await db.execute(
        select(Story)
        .where(
            Story.user_id == user_id,
            sa_func.to_tsvector("english", sa_func.coalesce(Story.title, "") + " " + sa_func.coalesce(Story.summary, "")).op("@@")(
                sa_func.plainto_tsquery("english", query)
            ),
        )
        .order_by(Story.best_score_with_this_story.desc().nulls_last())
        .limit(limit)
    )
    return list(result.scalars().all())


def _similar_insight(existing: str, new: str) -> bool:
    """Check if two coaching insights are semantically similar (simple heuristic)."""
    e_words = set(existing.lower().split())
    n_words = set(new.lower().split())
    if not e_words or not n_words:
        return False
    overlap = len(e_words & n_words) / max(len(e_words), len(n_words))
    return overlap > 0.6
