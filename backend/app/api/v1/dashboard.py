"""Dashboard API — aggregate stats for the user's main dashboard.

GET /api/v1/dashboard — all stats in one call (sessions, skills, stories, cost)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.interview_session import InterviewSession, SessionType
from app.models.segment_score import SegmentScore
from app.models.skill_graph_node import SkillGraphNode
from app.models.story import Story
from app.schemas.dashboard import DashboardResponse, RecentSession
from app.services.auth.dependencies import CurrentUser

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DashboardResponse:
    """Return aggregated dashboard stats for the current user."""
    now = datetime.now(UTC)
    cutoff_30d = now - timedelta(days=30)
    uid = current_user.id

    # ── Session stats ──────────────────────────────────────────────────────────

    # All sessions
    sess_result = await db.execute(select(InterviewSession).where(InterviewSession.user_id == uid))
    all_sessions = list(sess_result.scalars().all())

    total_sessions = len(all_sessions)
    sessions_last_30d = sum(1 for s in all_sessions if s.created_at >= cutoff_30d)
    sessions_scored = sum(1 for s in all_sessions if s.lint_results)
    total_cost = float(sum(s.total_cost_usd for s in all_sessions))
    cost_30d = float(sum(s.total_cost_usd for s in all_sessions if s.created_at >= cutoff_30d))

    # Negotiation sessions
    neg_sessions = [s for s in all_sessions if s.type == SessionType.NEGOTIATION]
    total_neg = len(neg_sessions)
    neg_scores = [
        (s.lint_results or {}).get("negotiation_analysis", {}).get("overall_score")
        for s in neg_sessions
    ]
    neg_scores_valid = [x for x in neg_scores if x]
    avg_neg_score = (
        round(sum(neg_scores_valid) / len(neg_scores_valid), 1) if neg_scores_valid else None
    )

    money_left_vals = [
        (s.lint_results or {}).get("negotiation_analysis", {}).get("money_left_on_table")
        for s in neg_sessions
    ]
    money_left_valid = [x for x in money_left_vals if x]
    avg_money_left = (
        int(sum(money_left_valid) / len(money_left_valid)) if money_left_valid else None
    )

    # Recent sessions (last 5)
    recent_raw = sorted(all_sessions, key=lambda s: s.created_at, reverse=True)[:5]
    recent_sessions = []
    for s in recent_raw:
        lr = s.lint_results or {}
        avg_score = lr.get("average_score") if "average_score" in lr else None
        recent_sessions.append(
            RecentSession(
                id=s.id,
                type=s.type,
                status=s.status,
                created_at=s.created_at,
                avg_score=avg_score,
                cost_usd=float(s.total_cost_usd),
            )
        )

    # ── Segment score stats ────────────────────────────────────────────────────

    scores_result = await db.execute(
        select(SegmentScore)
        .join(InterviewSession, SegmentScore.session_id == InterviewSession.id)
        .where(InterviewSession.user_id == uid)
    )
    all_seg_scores = list(scores_result.scalars().all())

    avg_score_all = (
        round(sum(s.overall_score for s in all_seg_scores) / len(all_seg_scores), 1)
        if all_seg_scores
        else None
    )
    best_score = max((s.overall_score for s in all_seg_scores), default=None)

    # Last 30 days scores
    recent_session_ids = {s.id for s in all_sessions if s.created_at >= cutoff_30d}
    recent_scores = [s for s in all_seg_scores if s.session_id in recent_session_ids]
    avg_score_30d = (
        round(sum(s.overall_score for s in recent_scores) / len(recent_scores), 1)
        if recent_scores
        else None
    )

    # ── Skill graph ────────────────────────────────────────────────────────────

    skills_result = await db.execute(select(SkillGraphNode).where(SkillGraphNode.user_id == uid))
    skill_nodes = list(skills_result.scalars().all())

    total_skills = len(skill_nodes)
    avg_skill = (
        round(sum(n.current_score for n in skill_nodes) / total_skills, 1) if skill_nodes else None
    )
    weakest = min(skill_nodes, key=lambda n: n.current_score).skill_name if skill_nodes else None
    strongest = max(skill_nodes, key=lambda n: n.current_score).skill_name if skill_nodes else None

    # ── Stories ────────────────────────────────────────────────────────────────

    stories_result = await db.execute(select(Story).where(Story.user_id == uid))
    stories = list(stories_result.scalars().all())
    total_stories = len(stories)

    from app.models.story import COMPETENCIES

    covered_comps = set()
    for story in stories:
        covered_comps.update(story.competencies or [])
    coverage_pct = round(len(covered_comps) / len(COMPETENCIES) * 100, 1) if COMPETENCIES else 0.0

    # ── Readiness estimate ─────────────────────────────────────────────────────
    # Simple formula: weighted avg of skill score + session count signal
    readiness: int | None = None
    if avg_skill is not None:
        session_signal = min(30, total_sessions * 3)  # up to +30 for sessions
        story_signal = min(10, total_stories * 2)  # up to +10 for stories
        raw = (avg_skill * 0.6) + session_signal + story_signal
        readiness = min(100, int(raw))

    logger.info(
        "dashboard.fetched",
        user_id=str(uid),
        total_sessions=total_sessions,
        total_skills=total_skills,
        readiness=readiness,
    )

    return DashboardResponse(
        total_sessions=total_sessions,
        sessions_last_30_days=sessions_last_30d,
        sessions_scored=sessions_scored,
        avg_score_all_time=avg_score_all,
        avg_score_last_30_days=avg_score_30d,
        best_session_score=best_score,
        total_skills_tracked=total_skills,
        avg_skill_score=avg_skill,
        weakest_skill=weakest,
        strongest_skill=strongest,
        total_stories=total_stories,
        coverage_pct=coverage_pct,
        total_negotiation_sessions=total_neg,
        avg_negotiation_score=avg_neg_score,
        avg_money_left_on_table=avg_money_left,
        total_cost_usd=total_cost,
        cost_last_30_days=cost_30d,
        readiness_estimate=readiness,
        recent_sessions=recent_sessions,
    )
