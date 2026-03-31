"""Skill Graph service — CRUD + update logic.

Responsible for:
- Creating/retrieving skill graph nodes (one per user per microskill).
- Updating skill scores from scoring results (rules triggered + memory hints).
- Computing trends (improving / declining / stable).
- Scheduling next review via spaced repetition.

Rule → skill mapping defined in RULE_SKILL_MAP below.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_graph_node import SKILL_CATEGORIES, SkillGraphNode, SkillTrend

logger = structlog.get_logger(__name__)

# ── Rule → skill mapping ───────────────────────────────────────────────────────
# Each rubric rule, when triggered, maps to a skill node that gets a negative signal.
# Absence of a rule (not triggered) → positive signal for that skill.

RULE_SKILL_MAP: dict[str, str] = {
    "no_star_structure": "star_structure",
    "missing_result": "quantifiable_results",
    "result_not_specific": "quantifiable_results",
    "missing_metrics": "quantifiable_results",
    "no_tradeoff": "tradeoff_analysis",
    "no_assumptions": "capacity_estimation",
    "shallow_followup": "conciseness",
    "rambling": "conciseness",
    "filler_spike": "filler_word_control",
    "no_ownership": "ownership_signal",
    "no_scale_thinking": "scalability_thinking",
    "no_stakeholder_mgmt": "leadership_stories",
    "no_mentoring_signal": "mentoring_signal",
    "weak_anchor": "anchoring",
    "early_concession": "counter_strategy",
}

# Flat map: skill_name → category
_SKILL_CATEGORY: dict[str, str] = {
    skill: cat for cat, skills in SKILL_CATEGORIES.items() for skill in skills
}


# ── Spaced repetition schedule ─────────────────────────────────────────────────


def _next_review_days(score: int, trend: str) -> int:
    """Days until next review based on score + trend.

    Lower score + declining trend → practice sooner.
    """
    if score < 40:
        return 1
    if score < 60:
        return 3 if trend == SkillTrend.DECLINING else 4
    if score < 80:
        return 7 if trend == SkillTrend.DECLINING else 10
    return 14 if trend != SkillTrend.DECLINING else 7


def _compute_trend(old_score: int, new_score: int) -> str:
    """Determine trend from score change."""
    delta = new_score - old_score
    if delta >= 5:
        return SkillTrend.IMPROVING
    if delta <= -5:
        return SkillTrend.DECLINING
    return SkillTrend.STABLE


# ── SkillGraphService ──────────────────────────────────────────────────────────


class SkillGraphService:
    """All skill graph operations for one user."""

    async def get_or_create_node(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        skill_name: str,
    ) -> SkillGraphNode:
        """Return existing node or create a new one with default score 0."""
        result = await db.execute(
            select(SkillGraphNode).where(
                SkillGraphNode.user_id == user_id,
                SkillGraphNode.skill_name == skill_name,
            )
        )
        node = result.scalar_one_or_none()
        if node is not None:
            return node

        category = _SKILL_CATEGORY.get(skill_name, "other")
        node = SkillGraphNode(
            user_id=user_id,
            skill_name=skill_name,
            skill_category=category,
            current_score=0,
            best_score=0,
            trend=SkillTrend.STABLE,
            evidence_links=[],
            typical_mistakes=[],
        )
        db.add(node)
        await db.flush()  # get id without committing
        logger.info(
            "skill_graph.node_created",
            user_id=str(user_id),
            skill_name=skill_name,
            category=category,
        )
        return node

    async def get_user_graph(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[SkillGraphNode]:
        """Return all skill nodes for a user, ordered by category + skill name."""
        result = await db.execute(
            select(SkillGraphNode)
            .where(SkillGraphNode.user_id == user_id)
            .order_by(SkillGraphNode.skill_category, SkillGraphNode.skill_name)
        )
        return list(result.scalars().all())

    async def update_from_scoring_result(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        segment_index: int,
        overall_score: int,
        rules_triggered: list[dict[str, Any]],
        memory_hints: dict[str, Any],
        question_type: str,
    ) -> list[SkillGraphNode]:
        """Update skill nodes based on a scoring result.

        Sources of skill signals:
        1. rules_triggered (negative signals — rule fired means skill weakness)
        2. memory_hints.skill_signals (LLM-detected positive/negative signals)

        Returns the list of updated nodes.
        """
        now = datetime.now(UTC)
        triggered_rule_ids = {r["rule"] for r in rules_triggered}
        updated_nodes: list[SkillGraphNode] = []

        # Build skill signals: {skill_name: ("positive" | "negative", note)}
        skill_signals: dict[str, tuple[str, str]] = {}

        # From rules triggered → negative signals on mapped skills
        for rule_id in triggered_rule_ids:
            skill = RULE_SKILL_MAP.get(rule_id)
            if skill:
                # Strongest negative signal: "strong" confidence rule triggers
                confidence = next(
                    (r.get("confidence", "weak") for r in rules_triggered if r["rule"] == rule_id),
                    "weak",
                )
                note = f"Rule '{rule_id}' triggered (confidence: {confidence})"
                skill_signals[skill] = ("negative", note)

        # From memory_hints.skill_signals → may override or add positive signals
        for sig in memory_hints.get("skill_signals", []):
            skill_name = sig.get("skill", "")
            direction = sig.get("direction", "positive")
            note = sig.get("note", "")
            if skill_name and skill_name in _SKILL_CATEGORY:
                # Positive signal from memory hints wins over absent negative
                if skill_name not in skill_signals or direction == "positive":
                    skill_signals[skill_name] = (direction, note)

        # Base signals from session type + overall_score — ensures the skill graph
        # always moves after scoring even when no rules fired and LLM emitted no hints.
        # Only fills in skills that have no stronger rule/hint signal yet.
        type_primary_skills: dict[str, list[str]] = {
            "system_design": [
                "tradeoff_analysis",
                "scalability_thinking",
                "capacity_estimation",
                "component_design",
                "failure_modes",
            ],
            "behavioral": ["star_structure", "quantifiable_results", "ownership_signal"],
            "coding_discussion": ["complexity_analysis", "edge_cases", "testing_approach"],
            "negotiation": ["anchoring", "value_articulation", "counter_strategy"],
            "debrief": ["confidence_under_pressure", "conciseness"],
            "diagnostic": ["star_structure", "conciseness"],
        }
        base_direction = "positive" if overall_score >= 60 else "negative"
        base_note = f"Inferred from overall_score={overall_score} ({question_type} session)"
        for skill in type_primary_skills.get(question_type, []):
            if skill not in skill_signals:
                skill_signals[skill] = (base_direction, base_note)

        # Apply signals to nodes
        for skill_name, (direction, note) in skill_signals.items():
            node = await self.get_or_create_node(db, user_id, skill_name)
            old_score = node.current_score

            # Score adjustment: ±(5-15) depending on overall_score proximity
            if direction == "positive":
                # Move toward overall_score from below
                delta = max(5, min(15, (overall_score - old_score) // 3))
                new_score = min(100, old_score + delta)
            else:
                # Negative: move score down, anchored by overall
                delta = max(3, min(10, (old_score - overall_score) // 3 + 5))
                new_score = max(0, old_score - delta)

            trend = _compute_trend(old_score, new_score)
            days = _next_review_days(new_score, trend)

            # Build evidence link
            evidence_link = {
                "session_id": str(session_id),
                "segment_index": segment_index,
                "score": new_score,
                "date": now.date().isoformat(),
                "note": note,
            }

            # Update mistake list for negative signals
            if direction == "negative" and note not in (node.typical_mistakes or []):
                mistakes = list(node.typical_mistakes or [])
                mistakes = (mistakes + [note])[-5:]  # keep last 5
                node.typical_mistakes = mistakes

            node.current_score = new_score
            node.best_score = max(node.best_score, new_score)
            node.trend = trend
            node.last_practiced = now
            node.next_review_due = now + timedelta(days=days)
            node.evidence_links = (list(node.evidence_links or []) + [evidence_link])[-20:]

            updated_nodes.append(node)
            logger.info(
                "skill_graph.node_updated",
                user_id=str(user_id),
                skill_name=skill_name,
                old_score=old_score,
                new_score=new_score,
                trend=trend,
                direction=direction,
            )

        return updated_nodes

    async def get_past_due_skills(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[SkillGraphNode]:
        """Return skills that are past their next_review_due date, worst first."""
        now = datetime.now(UTC)
        result = await db.execute(
            select(SkillGraphNode)
            .where(
                SkillGraphNode.user_id == user_id,
                SkillGraphNode.next_review_due <= now,
            )
            .order_by(SkillGraphNode.current_score, SkillGraphNode.next_review_due)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_weakest_skills(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[SkillGraphNode]:
        """Return lowest-scoring skills, prioritizing declining trend."""
        result = await db.execute(
            select(SkillGraphNode)
            .where(SkillGraphNode.user_id == user_id)
            .order_by(SkillGraphNode.current_score, SkillGraphNode.trend)
            .limit(limit)
        )
        return list(result.scalars().all())


# Module-level singleton
skill_graph_service = SkillGraphService()
