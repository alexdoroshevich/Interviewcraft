"""Drill planner — adaptive weekly practice schedule.

Uses spaced repetition logic from skill_graph.py to prioritize:
1. Past-due skills (review_due is in the past)
2. Low-score skills (score < 60)
3. Declining trend skills
4. Least recently practiced

Output: a weekly plan with Mon/Wed/Fri slots.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.skill_graph_node import SkillGraphNode, SkillTrend
from app.services.memory.skill_graph import skill_graph_service

logger = structlog.get_logger(__name__)

# Estimated minutes per drill slot
_MINS_PER_QUESTION = 7


def _urgency_score(node: SkillGraphNode) -> float:
    """Compute urgency score for drill ordering. Higher = more urgent."""
    now = datetime.now(UTC)
    score_urgency = (100 - node.current_score) / 100.0  # 0.0-1.0, higher = weaker

    # Past-due bonus
    past_due_bonus = 0.0
    if node.next_review_due:
        days_overdue = (now - node.next_review_due).total_seconds() / 86400
        past_due_bonus = min(0.5, max(0.0, days_overdue * 0.1))

    # Trend penalty
    trend_bonus = 0.0
    if node.trend == SkillTrend.DECLINING:
        trend_bonus = 0.2
    elif node.trend == SkillTrend.IMPROVING:
        trend_bonus = -0.1

    return score_urgency + past_due_bonus + trend_bonus


def _make_drill_slot(
    day: str,
    skill_name: str,
    skill_category: str,
    current_score: int,
    trend: str,
    questions: int,
    focus_note: str,
) -> dict[str, Any]:
    return {
        "day": day,
        "skill_name": skill_name,
        "skill_category": skill_category,
        "current_score": current_score,
        "trend": trend,
        "questions": questions,
        "estimated_minutes": questions * _MINS_PER_QUESTION,
        "focus_note": focus_note,
    }


def _focus_note(node: SkillGraphNode) -> str:
    """Generate a motivating focus note for a drill slot."""
    if node.current_score < 40:
        return f"Foundation needed — score {node.current_score}/100. Build the basics first."
    if node.trend == SkillTrend.DECLINING:
        return f"Slipping! Was {node.best_score}, now {node.current_score}. Reverse the trend."
    if node.best_score > node.current_score + 10:
        return (
            f"Beat Your Best: previous record {node.best_score}. "
            f"Can you top it? Currently {node.current_score}."
        )
    return (
        f"Keep building on {node.current_score}/100. Target: {min(100, node.current_score + 15)}."
    )


class DrillPlanner:
    """Generates a weekly drill plan for a user based on their skill graph."""

    async def generate_weekly_plan(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
        days_until: int | None = None,
    ) -> dict[str, Any]:
        """Return a weekly drill plan, optionally countdown-aware.

        Args:
            days_until: days until the interview. When set, slot count and
                        question volume scale with urgency.

        Returns a dict with:
          - slots: list of drill slot dicts
          - total_skills: int
          - weakest_skill: str | None
          - estimated_minutes_per_week: int
          - generated_at: str (ISO)
        """
        nodes = await skill_graph_service.get_user_graph(db, user_id)

        if not nodes:
            return {
                "slots": [],
                "total_skills": 0,
                "weakest_skill": None,
                "estimated_minutes_per_week": 0,
                "generated_at": datetime.now(UTC).isoformat(),
                "message": (
                    "No skill data yet. Complete an interview session "
                    "and score it to build your skill graph."
                ),
            }

        # Sort by urgency (highest first)
        ranked = sorted(nodes, key=_urgency_score, reverse=True)

        # Scale slot count and questions-per-slot based on days until interview
        if days_until is not None and days_until <= 7:
            # Critical — daily drilling, double questions
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            max_slots = min(7, len(ranked))
            base_questions = 3
        elif days_until is not None and days_until <= 21:
            # High urgency — 5 sessions/week
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            max_slots = min(5, len(ranked))
            base_questions = 2
        else:
            # Normal — Mon/Wed/Fri
            day_names = ["Monday", "Wednesday", "Friday"]
            max_slots = min(3, len(ranked))
            base_questions = 1

        slots = []
        for i in range(max_slots):
            node = ranked[i]
            questions = base_questions + (1 if node.current_score < 60 else 0)
            slots.append(
                _make_drill_slot(
                    day=day_names[i],
                    skill_name=node.skill_name,
                    skill_category=node.skill_category,
                    current_score=node.current_score,
                    trend=node.trend,
                    questions=questions,
                    focus_note=_focus_note(node),
                )
            )

        total_mins = sum(s["estimated_minutes"] for s in slots)
        weakest = ranked[0].skill_name if ranked else None

        logger.info(
            "drill_planner.plan_generated",
            user_id=str(user_id),
            total_skills=len(nodes),
            slots=len(slots),
            weakest_skill=weakest,
        )

        return {
            "slots": slots,
            "total_skills": len(nodes),
            "weakest_skill": weakest,
            "estimated_minutes_per_week": total_mins,
            "generated_at": datetime.now(UTC).isoformat(),
            "message": None,
        }

    async def get_best_scores(
        self,
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Return Beat Your Best data: skills where there's a personal record to beat."""
        nodes = await skill_graph_service.get_user_graph(db, user_id)

        best_list = []
        for node in nodes:
            if node.best_score > 0:
                best_list.append(
                    {
                        "skill_name": node.skill_name,
                        "skill_category": node.skill_category,
                        "current_score": node.current_score,
                        "best_score": node.best_score,
                        "gap": node.best_score - node.current_score,
                        "can_beat": node.current_score < node.best_score,
                    }
                )

        # Sort by gap (largest gap first — most room to improve vs personal best)
        return sorted(best_list, key=lambda x: x["gap"], reverse=True)


# Module-level singleton
drill_planner = DrillPlanner()
