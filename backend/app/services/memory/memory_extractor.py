"""Memory extractor — post-session skill + story extraction.

Uses a single Anthropic call (not Batch API for simplicity in MVP;
Batch API deferred to Phase 2 for 50% cost savings on async extraction).

Extracts:
- Skill signals (which skills improved/declined in this session)
- Story detected (was a compelling story told?)
- Communication profile notes

Results are used to update the skill graph and surface story-save prompts.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_graph_node import SKILL_CATEGORIES
from app.services.memory.skill_graph import skill_graph_service
from app.services.usage import log_usage
from app.services.voice.costs import calc_anthropic_cost

logger = structlog.get_logger(__name__)

_HAIKU = "claude-haiku-4-5-20251001"

# Flat list of all known skill names (for the extraction prompt)
_ALL_SKILLS = sorted({skill for skills in SKILL_CATEGORIES.values() for skill in skills})

_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["skill_signals", "story_detected", "story_title", "communication_notes"],
    "properties": {
        "skill_signals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["skill", "direction", "note"],
                "properties": {
                    "skill": {"type": "string"},
                    "direction": {"type": "string", "enum": ["positive", "negative"]},
                    "note": {"type": "string"},
                },
            },
        },
        "story_detected": {"type": "boolean"},
        "story_title": {"type": ["string", "null"]},
        "communication_notes": {"type": ["string", "null"]},
    },
}


class MemoryExtractor:
    """Extracts skill signals and stories from a completed session transcript."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def extract_and_update(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        transcript: list[dict[str, Any]],
        segment_scores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Extract memory from session and update skill graph.

        Args:
            transcript: List of {role, content, ts_ms} dicts.
            segment_scores: List of scored segment dicts (from ScoringResult).

        Returns dict with extraction result and updated skill names.
        """
        if not transcript or not segment_scores:
            return {
                "skill_signals": [],
                "story_detected": False,
                "story_title": None,
                "communication_notes": None,
                "updated_skills": [],
            }

        prompt = _build_extraction_prompt(transcript, segment_scores)

        try:
            extraction = await self._call_anthropic(prompt, session_id, user_id, db)
        except Exception as exc:
            logger.error(
                "memory_extractor.extraction_failed",
                session_id=str(session_id),
                error=str(exc),
            )
            return {
                "skill_signals": [],
                "story_detected": False,
                "story_title": None,
                "communication_notes": None,
                "updated_skills": [],
            }

        # Update skill graph using aggregated signals from the session
        # We use the overall session average score as context
        avg_score = (
            sum(s.get("overall_score", 50) for s in segment_scores) // len(segment_scores)
            if segment_scores
            else 50
        )
        # Combine extraction signals with all rules from all scored segments
        all_rules_triggered = [
            rule for seg in segment_scores for rule in seg.get("rules_triggered", [])
        ]

        updated_nodes = await skill_graph_service.update_from_scoring_result(
            db=db,
            user_id=user_id,
            session_id=session_id,
            segment_index=-1,  # -1 = session-level update
            overall_score=avg_score,
            rules_triggered=all_rules_triggered,
            memory_hints=extraction,
            question_type="behavioral",  # broad update
        )
        await db.commit()

        return {
            "skill_signals": extraction.get("skill_signals", []),
            "story_detected": extraction.get("story_detected", False),
            "story_title": extraction.get("story_title"),
            "communication_notes": extraction.get("communication_notes"),
            "updated_skills": [n.skill_name for n in updated_nodes],
        }

    async def _call_anthropic(
        self,
        prompt: str,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Single Anthropic call for memory extraction. Uses Haiku (cheap)."""
        response = await self._client.messages.create(
            model=_HAIKU,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": "extract_memory",
                    "description": "Extract skill signals and story from interview session",
                    "input_schema": _EXTRACTION_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "extract_memory"},
        )

        usage = response.usage
        cost = calc_anthropic_cost(
            model=_HAIKU,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=0,
        )
        await log_usage(
            db=db,
            session_id=session_id,
            user_id=user_id,
            provider="anthropic",
            operation="memory_llm",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=0,
            cost_usd=cost,
            latency_ms=0,
            quality_profile="balanced",
            cached=False,
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_memory":
                return cast(dict[str, Any], block.input)

        raise ValueError("No tool_use block returned from memory extraction")


# ── Prompt builder ─────────────────────────────────────────────────────────────


def _build_extraction_prompt(
    transcript: list[dict[str, Any]],
    segment_scores: list[dict[str, Any]],
) -> str:
    """Build the memory extraction prompt from session data."""
    transcript_text = "\n".join(
        f"[{t.get('ts_ms', 0)}ms] {'INTERVIEWER' if t.get('role') == 'assistant' else 'CANDIDATE'}: "
        f"{t.get('content', '')}"
        for t in transcript[:40]  # cap to first 40 turns for token efficiency
    )

    scores_text = "\n".join(
        f"Segment {s.get('segment_index', i)}: score={s.get('overall_score', 'N/A')}, "
        f"rules={[r.get('rule') for r in s.get('rules_triggered', [])]}"
        for i, s in enumerate(segment_scores)
    )

    known_skills = ", ".join(_ALL_SKILLS)

    return f"""Analyze this interview session and extract skill signals and story information.

=== KNOWN SKILLS ===
{known_skills}

=== SESSION TRANSCRIPT (first 40 turns) ===
{transcript_text}

=== SCORING SUMMARY ===
{scores_text}

Extract:
1. skill_signals: For each skill that showed clear evidence (positive or negative), return a signal.
   - Only include skills from the known skills list.
   - "positive" = candidate demonstrated this skill well.
   - "negative" = candidate struggled with this skill.
   - Include specific, brief notes about what you observed.

2. story_detected: Was a notable personal/professional story told? (True/False)

3. story_title: If story_detected=True, a short title (e.g. "Database Migration at Startup X")

4. communication_notes: Brief note about overall communication style (pacing, confidence, clarity).

Keep all notes brief (1 sentence max per item).
"""
