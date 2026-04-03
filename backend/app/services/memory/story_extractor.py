"""Story extractor — detect and extract stories from session transcripts.

Uses Anthropic (Haiku) to:
1. Detect if a compelling story was told in the session.
2. Extract title, summary, and competencies covered.
3. Return a StoryProposal for the user to accept or reject.

Integration:
- Called after scoring in `POST /sessions/{id}/score`
- Also callable standalone via `POST /sessions/{id}/story-proposal`
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import structlog
from anthropic import AsyncAnthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import COMPETENCIES, Story
from app.services.usage import log_usage
from app.services.voice.costs import calc_anthropic_cost

logger = structlog.get_logger(__name__)

_HAIKU = "claude-haiku-4-5"

_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["story_detected", "title", "summary", "competencies"],
    "properties": {
        "story_detected": {"type": "boolean"},
        "title": {"type": ["string", "null"]},
        "summary": {"type": ["string", "null"]},
        "competencies": {
            "type": "array",
            "items": {"type": "string"},
        },
        "overuse_warning": {"type": ["string", "null"]},
    },
}


class StoryExtractor:
    """Detect and extract stories from session transcripts."""

    def __init__(self, api_key: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)

    async def extract_story_proposal(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        transcript: list[dict[str, Any]],
        story_hint: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract a story proposal from a session transcript.

        Args:
            transcript: List of {role, content, ts_ms} dicts.
            story_hint: LLM-provided title hint from memory_hints (may be None).

        Returns:
            Dict with story proposal or None if no story detected.
        """
        if not transcript:
            return None

        # Check if already saved from this session
        existing = await db.execute(
            select(Story).where(
                Story.user_id == user_id,
                Story.source_session_id == session_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None  # already extracted and saved

        prompt = _build_extraction_prompt(transcript, story_hint)

        try:
            result = await self._call_anthropic(prompt, session_id, user_id, db)
        except Exception as exc:
            logger.error(
                "story_extractor.extraction_failed",
                session_id=str(session_id),
                error=str(exc),
            )
            return None

        if not result.get("story_detected") or not result.get("title"):
            return None

        # Validate competencies against known list
        valid_competencies = [c for c in (result.get("competencies") or []) if c in COMPETENCIES]

        logger.info(
            "story_extractor.story_detected",
            session_id=str(session_id),
            title=result.get("title"),
            competencies=valid_competencies,
        )

        return {
            "session_id": str(session_id),
            "proposed_title": result["title"],
            "proposed_summary": result.get("summary", ""),
            "proposed_competencies": valid_competencies,
            "already_saved": False,
        }

    async def _call_anthropic(
        self,
        prompt: str,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Single Haiku call for story extraction."""
        response = await self._client.messages.create(
            model=_HAIKU,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
            tools=[
                {
                    "name": "extract_story",
                    "description": "Extract story information from interview session",
                    "input_schema": _EXTRACTION_SCHEMA,
                }
            ],
            tool_choice={"type": "tool", "name": "extract_story"},
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
            operation="story_llm",
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=0,
            cost_usd=cost,
            latency_ms=0,
            quality_profile="balanced",
            cached=False,
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "extract_story":
                return cast(dict[str, Any], block.input)

        raise ValueError("No tool_use block from story extraction")


def _build_extraction_prompt(
    transcript: list[dict[str, Any]],
    story_hint: str | None,
) -> str:
    """Build the story extraction prompt."""
    transcript_text = "\n".join(
        f"{'INTERVIEWER' if t.get('role') == 'assistant' else 'CANDIDATE'}: {t.get('content', '')}"
        for t in transcript[:30]  # cap for token efficiency
    )

    competencies_list = "\n".join(f"  - {c}" for c in COMPETENCIES)
    hint_note = (
        f"\nNote: A story titled '{story_hint}' may have been detected." if story_hint else ""
    )

    return f"""Analyze this interview session transcript and detect if a compelling personal/professional story was told.{hint_note}

=== TRANSCRIPT ===
{transcript_text}

=== KNOWN COMPETENCIES ===
{competencies_list}

Extract:
1. story_detected: Was a clear, notable personal/professional story told? (True/False)
   A story has: context (where/when), a specific challenge, actions taken, result.

2. title: Short descriptive title (e.g., "Database Migration at Startup X"). Null if no story.

3. summary: One sentence summary of the story. Null if no story.
   Format: "[Verb] [what] for [context/outcome]"
   Example: "Led PostgreSQL → DynamoDB migration for 500M records at 2x throughput"

4. competencies: Which competencies does this story demonstrate? Only use competencies from the list above.
   Maximum 3 competencies.

5. overuse_warning: If the candidate mentioned they've used this story many times, note it. Otherwise null.

Be conservative — only detect=True if a clear, substantive story exists. Generic answers don't count.
"""
