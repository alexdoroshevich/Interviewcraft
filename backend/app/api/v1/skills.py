"""Skills API — skill graph, drill plan, and Beat Your Best.

GET  /api/v1/skills            — full skill graph for current user
GET  /api/v1/skills/plan       — weekly adaptive drill plan
GET  /api/v1/skills/history    — per-skill history (trend over time)
GET  /api/v1/skills/best       — Beat Your Best data
"""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.skills import (
    BeatYourBestItem,
    DrillPlanResponse,
    DrillSlot,
    SkillGraphResponse,
    SkillHistoryPoint,
    SkillHistoryResponse,
    SkillNodeResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.memory.drill_planner import drill_planner
from app.services.memory.skill_graph import skill_graph_service

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/skills", tags=["skills"])


# ── GET /api/v1/skills ────────────────────────────────────────────────────────


@router.get("", response_model=SkillGraphResponse)
async def get_skill_graph(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SkillGraphResponse:
    """Return the full skill graph for the authenticated user."""
    nodes = await skill_graph_service.get_user_graph(db, current_user.id)

    if not nodes:
        return SkillGraphResponse(
            user_id=current_user.id,
            total_skills=0,
            nodes=[],
            avg_score=0.0,
            weakest_category=None,
            strongest_category=None,
        )

    avg_score = sum(n.current_score for n in nodes) / len(nodes)

    # Category averages
    cat_scores: dict[str, list[int]] = defaultdict(list)
    for n in nodes:
        cat_scores[n.skill_category].append(n.current_score)

    cat_avgs = {cat: sum(scores) / len(scores) for cat, scores in cat_scores.items()}
    weakest = min(cat_avgs, key=cat_avgs.get) if cat_avgs else None  # type: ignore[arg-type]
    strongest = max(cat_avgs, key=cat_avgs.get) if cat_avgs else None  # type: ignore[arg-type]

    return SkillGraphResponse(
        user_id=current_user.id,
        total_skills=len(nodes),
        nodes=[SkillNodeResponse.model_validate(n) for n in nodes],
        avg_score=round(avg_score, 1),
        weakest_category=weakest,
        strongest_category=strongest,
    )


# ── GET /api/v1/skills/plan ───────────────────────────────────────────────────


@router.get("/plan", response_model=DrillPlanResponse)
async def get_drill_plan(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DrillPlanResponse:
    """Return the adaptive weekly drill plan."""
    plan = await drill_planner.generate_weekly_plan(db, current_user.id)

    return DrillPlanResponse(
        slots=[DrillSlot(**s) for s in plan["slots"]],
        total_skills=plan["total_skills"],
        weakest_skill=plan["weakest_skill"],
        estimated_minutes_per_week=plan["estimated_minutes_per_week"],
        generated_at=plan["generated_at"],
        message=plan.get("message"),
    )


# ── GET /api/v1/skills/history ────────────────────────────────────────────────


@router.get("/history", response_model=list[SkillHistoryResponse])
async def get_skill_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SkillHistoryResponse]:
    """Return skill trend history (per evidence link) for all skills."""
    nodes = await skill_graph_service.get_user_graph(db, current_user.id)
    result = []

    for node in nodes:
        history = [
            SkillHistoryPoint(
                date=link.get("date", ""),
                score=link.get("score", 0),
                session_id=link.get("session_id"),
            )
            for link in (node.evidence_links or [])
        ]
        result.append(
            SkillHistoryResponse(
                skill_name=node.skill_name,
                current_score=node.current_score,
                best_score=node.best_score,
                trend=node.trend,
                history=history,
            )
        )

    return result


# ── GET /api/v1/skills/best ───────────────────────────────────────────────────


@router.get("/best", response_model=list[BeatYourBestItem])
async def get_beat_your_best(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[BeatYourBestItem]:
    """Return Beat Your Best data for each skill with a recorded personal best."""
    items = await drill_planner.get_best_scores(db, current_user.id)
    return [BeatYourBestItem(**item) for item in items]
