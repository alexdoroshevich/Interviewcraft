"""Portfolio export endpoint.

GET /api/v1/portfolio/export?visibility=private|public

Returns a JSON snapshot of the user's training data.

private  — full details (transcripts, scores, stories, skill graph)
public   — public-safe: trends + deltas + skill graph only (no PII, no transcripts)

Used for:
  - Sharing progress with recruiters / team
  - Blog posts ("how I improved my system design score")
  - Open source portfolio demos
"""

from datetime import UTC, datetime
from typing import Annotated, Literal
import typing

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.interview_session import InterviewSession
from app.models.segment_score import SegmentScore
from app.models.skill_graph_node import SkillGraphNode
from app.models.story import Story
from app.services.auth.dependencies import CurrentUser

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/portfolio", tags=["portfolio"])


@router.get("/export")
async def export_portfolio(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    visibility: Literal["private", "public"] = Query(default="public"),
) -> dict[str, typing.Any]:
    """Export training portfolio as JSON.

    public  — safe to share: skill graph, score trends, session counts, deltas.
    private — includes story bank, session types, score breakdowns (no transcripts).
    """
    now = datetime.now(tz=UTC).isoformat()

    # Skill graph
    skill_rows = await db.execute(
        select(SkillGraphNode).where(SkillGraphNode.user_id == current_user.id)
    )
    skills = skill_rows.scalars().all()

    skill_data = [
        {
            "skill": s.skill_name,
            "category": s.skill_category,
            "score": s.current_score,
            "trend": s.trend,
            "best_score": s.best_score,
            "sessions_count": len(s.evidence_links),
        }
        for s in sorted(skills, key=lambda x: x.skill_category)
    ]

    # Sessions (counts + score trends only — no transcript content)
    sess_rows = await db.execute(
        select(InterviewSession)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(InterviewSession.created_at)
    )
    sessions = sess_rows.scalars().all()

    seg_rows = await db.execute(
        select(SegmentScore)
        .join(InterviewSession, SegmentScore.session_id == InterviewSession.id)
        .where(InterviewSession.user_id == current_user.id)
        .order_by(SegmentScore.created_at)
    )
    segments = seg_rows.scalars().all()

    session_summary = [
        {
            "type": s.type,
            "status": s.status,
            "date": s.created_at.date().isoformat(),
            "avg_score": (
                round(
                    sum(seg.overall_score for seg in segments if str(seg.session_id) == str(s.id))
                    / max(
                        1,
                        sum(1 for seg in segments if str(seg.session_id) == str(s.id)),
                    ),
                    1,
                )
                if any(str(seg.session_id) == str(s.id) for seg in segments)
                else None
            ),
            "rewound_segments": sum(
                1 for seg in segments if str(seg.session_id) == str(s.id) and seg.rewind_count > 0
            ),
        }
        for s in sessions
        if s.status == "completed"
    ]

    base = {
        "exported_at": now,
        "visibility": visibility,
        "skill_graph": skill_data,
        "session_count": len([s for s in sessions if s.status == "completed"]),
        "session_summary": session_summary,
        "avg_score_all_time": (
            round(sum(seg.overall_score for seg in segments) / len(segments), 1)
            if segments
            else None
        ),
        "total_rewound_segments": sum(1 for seg in segments if seg.rewind_count > 0),
    }

    if visibility == "private":
        # Add stories (private — personal career narratives)
        story_rows = await db.execute(select(Story).where(Story.user_id == current_user.id))
        stories = story_rows.scalars().all()
        base["stories"] = [
            {
                "title": s.title,
                "summary": s.summary,
                "competencies": s.competencies,
                "times_used": s.times_used,
                "best_score": s.best_score_with_this_story,
            }
            for s in stories
        ]
        # Score breakdowns (category scores) — no transcript text
        base["segment_scores"] = [
            {
                "date": seg.created_at.date().isoformat(),
                "overall": seg.overall_score,
                "categories": seg.category_scores,
                "rewind_count": seg.rewind_count,
                "best_rewind_score": seg.best_rewind_score,
            }
            for seg in segments
        ]

    logger.info(
        "portfolio.export",
        user_id=str(current_user.id),
        visibility=visibility,
        session_count=base["session_count"],
    )
    return base
