"""Skills API — skill graph, drill plan, and Beat Your Best.

GET  /api/v1/skills            — full skill graph for current user
GET  /api/v1/skills/plan       — weekly adaptive drill plan
GET  /api/v1/skills/history    — per-skill history (trend over time)
GET  /api/v1/skills/best       — Beat Your Best data
"""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from sqlalchemy import select

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.skills import (
    BeatYourBestItem,
    BenchmarkResponse,
    DrillPlanResponse,
    DrillSlot,
    SkillGraphResponse,
    SkillHistoryPoint,
    SkillHistoryResponse,
    SkillNodeResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.models.skill_graph_node import SkillGraphNode
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
    """Return the adaptive weekly drill plan, countdown-aware if interview date is set."""
    from datetime import UTC, date, datetime

    # Read interview date from profile
    profile = current_user.profile or {}
    raw_date = profile.get("interview_date")
    days_until: int | None = None
    urgency: str | None = None

    if raw_date:
        interview_date = date.fromisoformat(raw_date)
        today = datetime.now(tz=UTC).date()
        days = (interview_date - today).days
        if days >= 0:
            days_until = days
            if days <= 7:
                urgency = "critical"
            elif days <= 21:
                urgency = "high"
            elif days <= 60:
                urgency = "normal"
            else:
                urgency = "relaxed"

    plan = await drill_planner.generate_weekly_plan(db, current_user.id, days_until=days_until)

    return DrillPlanResponse(
        slots=[DrillSlot(**s) for s in plan["slots"]],
        total_skills=plan["total_skills"],
        weakest_skill=plan["weakest_skill"],
        estimated_minutes_per_week=plan["estimated_minutes_per_week"],
        generated_at=plan["generated_at"],
        message=plan.get("message"),
        days_until_interview=days_until,
        interview_urgency=urgency,
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


# ── GET /api/v1/skills/benchmark ──────────────────────────────────────────────


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BenchmarkResponse:
    """Return peer benchmark: current user's percentile rank vs all users.

    Computes per-user average scores across all skill nodes, then ranks
    the current user within that distribution. Only users with at least
    one scored skill node are included in the pool.
    """
    result = await db.execute(select(SkillGraphNode))
    all_nodes = list(result.scalars().all())

    if not all_nodes:
        return BenchmarkResponse(
            overall_percentile=0,
            by_category={},
            your_avg_score=0.0,
            platform_avg_score=0.0,
            sample_size=0,
        )

    # Group nodes by user
    user_nodes: dict = defaultdict(list)
    for node in all_nodes:
        user_nodes[node.user_id].append(node)

    # Per-user overall avg score
    user_avgs: dict = {
        uid: sum(n.current_score for n in nodes) / len(nodes)
        for uid, nodes in user_nodes.items()
    }

    # Per-user per-category avg
    user_cat_avgs: dict = {}
    for uid, nodes in user_nodes.items():
        cat_map: dict[str, list[int]] = defaultdict(list)
        for n in nodes:
            cat_map[n.skill_category].append(n.current_score)
        user_cat_avgs[uid] = {
            cat: sum(scores) / len(scores) for cat, scores in cat_map.items()
        }

    sample_size = len(user_avgs)
    all_avg_scores = sorted(user_avgs.values())
    platform_avg = sum(all_avg_scores) / len(all_avg_scores)

    # Current user's overall avg
    my_nodes = user_nodes.get(current_user.id, [])
    my_avg = (
        sum(n.current_score for n in my_nodes) / len(my_nodes) if my_nodes else 0.0
    )

    # Percentile = fraction of users scoring below the current user
    overall_pct = (
        int(sum(1 for s in all_avg_scores if s < my_avg) / sample_size * 100)
        if sample_size > 0
        else 0
    )

    # Per-category percentiles
    all_categories = {n.skill_category for n in all_nodes}
    by_category: dict[str, int] = {}
    my_cat_avgs = user_cat_avgs.get(current_user.id, {})

    for cat in all_categories:
        cat_scores = sorted(
            v[cat] for v in user_cat_avgs.values() if cat in v
        )
        my_cat_score = my_cat_avgs.get(cat, 0.0)
        if cat_scores:
            pct = int(sum(1 for s in cat_scores if s < my_cat_score) / len(cat_scores) * 100)
        else:
            pct = 0
        by_category[cat] = pct

    logger.info(
        "skills.benchmark",
        user_id=str(current_user.id),
        overall_percentile=overall_pct,
        sample_size=sample_size,
    )

    return BenchmarkResponse(
        overall_percentile=overall_pct,
        by_category=by_category,
        your_avg_score=round(my_avg, 1),
        platform_avg_score=round(platform_avg, 1),
        sample_size=sample_size,
    )
