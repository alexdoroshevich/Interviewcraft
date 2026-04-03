"""Admin metrics dashboard + question moderation.

GET  /api/v1/admin/metrics                  — requires admin role.
GET  /api/v1/admin/questions/pending        — list pending contributions.
POST /api/v1/admin/questions/{id}/approve   — approve a question.
POST /api/v1/admin/questions/{id}/reject    — reject a question.
POST /api/v1/admin/memory/consolidate       — trigger Batch API memory consolidation.

Aggregates:
- Voice pipeline latency p50/p95 (session_metrics, last 7 days)
- Scoring quality: avg score, stddev, rewind rate (last 30 days)
- Usage: sessions, cost, Anthropic cache hit rate (last 30 days)
- Daily latency trend (last 14 days) for Recharts

DoD KPIs tracked here:
  ✅ e2e latency p95 < 1000ms
  ✅ cache hit rate > 70%
  ✅ session completion rate > 60%
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import Float, Integer, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.interview_session import InterviewSession
from app.models.question import Question
from app.models.segment_score import SegmentScore
from app.models.session_metrics import SessionMetrics
from app.models.usage_log import UsageLog
from app.schemas.admin import (
    AdminMetricsResponse,
    DailyLatencyPoint,
    LatencyPercentiles,
    ScoringMetrics,
    UsageMetrics,
    VoiceLatencyMetrics,
)
from app.services.auth.dependencies import CurrentAdmin

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _p(val: float | None) -> float | None:
    """Round percentile to 1 decimal, or None."""
    return round(val, 1) if val is not None else None


@router.get("/metrics", response_model=AdminMetricsResponse)
async def get_metrics(
    _admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminMetricsResponse:
    """Return aggregated metrics for the admin dashboard.

    All queries are read-only aggregations — no PII returned.
    """
    now = datetime.now(tz=UTC)
    since_7d = now - timedelta(days=7)
    since_14d = now - timedelta(days=14)
    since_30d = now - timedelta(days=30)

    # ── Voice latency p50/p95 (7-day) ─────────────────────────────────────────

    lat = await db.execute(
        select(
            func.percentile_cont(0.5).within_group(SessionMetrics.stt_latency_ms).label("stt_p50"),
            func.percentile_cont(0.95).within_group(SessionMetrics.stt_latency_ms).label("stt_p95"),
            func.percentile_cont(0.5).within_group(SessionMetrics.llm_ttft_ms).label("llm_p50"),
            func.percentile_cont(0.95).within_group(SessionMetrics.llm_ttft_ms).label("llm_p95"),
            func.percentile_cont(0.5).within_group(SessionMetrics.tts_latency_ms).label("tts_p50"),
            func.percentile_cont(0.95).within_group(SessionMetrics.tts_latency_ms).label("tts_p95"),
            func.percentile_cont(0.5).within_group(SessionMetrics.e2e_latency_ms).label("e2e_p50"),
            func.percentile_cont(0.95).within_group(SessionMetrics.e2e_latency_ms).label("e2e_p95"),
            func.count(SessionMetrics.id).label("n"),
        ).where(SessionMetrics.created_at >= since_7d)
    )
    row = lat.one()

    voice_7d = VoiceLatencyMetrics(
        stt=LatencyPercentiles(p50=_p(row.stt_p50), p95=_p(row.stt_p95)),
        llm_ttft=LatencyPercentiles(p50=_p(row.llm_p50), p95=_p(row.llm_p95)),
        tts=LatencyPercentiles(p50=_p(row.tts_p50), p95=_p(row.tts_p95)),
        e2e=LatencyPercentiles(p50=_p(row.e2e_p50), p95=_p(row.e2e_p95)),
        sample_count=row.n or 0,
    )

    # ── Scoring quality (30-day) ───────────────────────────────────────────────

    score_row = await db.execute(
        select(
            func.avg(cast(SegmentScore.overall_score, Float)).label("avg_score"),
            func.stddev(cast(SegmentScore.overall_score, Float)).label("stddev"),
            func.count(SegmentScore.id).label("total"),
            func.sum(cast(SegmentScore.rewind_count > 0, Integer)).label("rewound"),
        ).where(SegmentScore.created_at >= since_30d)
    )
    sr = score_row.one()
    total_scored = sr.total or 0
    rewound = sr.rewound or 0
    rewind_rate = round((rewound / total_scored * 100), 1) if total_scored else 0.0

    scoring_30d = ScoringMetrics(
        avg_score=round(float(sr.avg_score), 1) if sr.avg_score else None,
        score_stddev=round(float(sr.stddev), 1) if sr.stddev else None,
        total_scored=total_scored,
        rewind_rate_pct=rewind_rate,
    )

    # ── Usage + cost (30-day) ──────────────────────────────────────────────────

    sess_row = await db.execute(
        select(
            func.count(InterviewSession.id).label("total"),
            func.sum(cast(InterviewSession.status == "completed", Integer)).label("completed"),
        ).where(InterviewSession.created_at >= since_30d)
    )
    sess = sess_row.one()
    total_sessions = sess.total or 0
    completed_sessions = sess.completed or 0
    completion_rate = round(completed_sessions / total_sessions * 100, 1) if total_sessions else 0.0

    usage_row = await db.execute(
        select(
            func.count(UsageLog.id).label("total_calls"),
            func.coalesce(func.sum(UsageLog.cost_usd), 0).label("total_cost"),
            func.sum(cast(UsageLog.cached.is_(True), Integer)).label("cached_calls"),
            func.sum(
                cast(
                    (UsageLog.provider == "anthropic") & UsageLog.cached.is_(True),
                    Integer,
                )
            ).label("anthropic_cached"),
            func.sum(cast(UsageLog.provider == "anthropic", Integer)).label("anthropic_total"),
        ).where(UsageLog.created_at >= since_30d)
    )
    ur = usage_row.one()
    total_cost = float(ur.total_cost or 0)
    cost_per_session = round(total_cost / total_sessions, 4) if total_sessions else 0.0
    anthropic_total = ur.anthropic_total or 0
    anthropic_cached = ur.anthropic_cached or 0
    cache_hit_rate = round(anthropic_cached / anthropic_total * 100, 1) if anthropic_total else 0.0

    usage_30d = UsageMetrics(
        total_sessions=total_sessions,
        completed_sessions=completed_sessions,
        completion_rate_pct=completion_rate,
        total_cost_usd=round(total_cost, 4),
        cost_per_session_usd=cost_per_session,
        cache_hit_rate_pct=cache_hit_rate,
        total_api_calls=ur.total_calls or 0,
    )

    # ── Daily latency trend (last 14 days) ────────────────────────────────────

    trend_rows = await db.execute(
        text("""
            SELECT
                DATE(created_at AT TIME ZONE 'UTC') AS day,
                percentile_cont(0.5) WITHIN GROUP (ORDER BY e2e_latency_ms) AS e2e_p50,
                percentile_cont(0.95) WITHIN GROUP (ORDER BY e2e_latency_ms) AS e2e_p95
            FROM session_metrics
            WHERE created_at >= :since
              AND e2e_latency_ms IS NOT NULL
            GROUP BY day
            ORDER BY day
        """),
        {"since": since_14d},
    )
    latency_trend = [
        DailyLatencyPoint(
            date=str(r.day),
            e2e_p50=_p(r.e2e_p50),
            e2e_p95=_p(r.e2e_p95),
        )
        for r in trend_rows
    ]

    # ── KPI flags ─────────────────────────────────────────────────────────────

    e2e_p95 = voice_7d.e2e.p95
    kpi_latency_ok = e2e_p95 is not None and e2e_p95 < 1000
    kpi_cache_ok = cache_hit_rate >= 70.0
    kpi_completion_ok = completion_rate >= 60.0

    logger.info(
        "admin.metrics.fetched",
        sample_count=voice_7d.sample_count,
        e2e_p95=e2e_p95,
        cache_hit_rate=cache_hit_rate,
        completion_rate=completion_rate,
    )

    return AdminMetricsResponse(
        voice_7d=voice_7d,
        scoring_30d=scoring_30d,
        usage_30d=usage_30d,
        latency_trend=latency_trend,
        kpi_latency_ok=kpi_latency_ok,
        kpi_cache_ok=kpi_cache_ok,
        kpi_completion_ok=kpi_completion_ok,
    )


# ── Question moderation ───────────────────────────────────────────────────────

from app.schemas.skills import QuestionResponse  # noqa: E402 — avoid circular at module level


@router.get("/questions/pending", response_model=list[QuestionResponse])
async def list_pending_questions(
    _admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> list[QuestionResponse]:
    """Return questions awaiting admin review (status='pending')."""
    result = await db.execute(
        select(Question)
        .where(Question.status == "pending")
        .order_by(Question.created_at)
        .limit(limit)
    )
    return [QuestionResponse.model_validate(q) for q in result.scalars().all()]


@router.post("/questions/{question_id}/approve", status_code=status.HTTP_204_NO_CONTENT)
async def approve_question(
    question_id: uuid.UUID,
    _admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Approve a pending question — it will appear in the question bank."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    q.status = "approved"
    await db.commit()
    logger.info("admin.question_approved", question_id=str(question_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/questions/{question_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_question(
    question_id: uuid.UUID,
    _admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Reject a pending question — it will not appear in the question bank."""
    result = await db.execute(select(Question).where(Question.id == question_id))
    q = result.scalar_one_or_none()
    if q is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found.")
    q.status = "rejected"
    await db.commit()
    logger.info("admin.question_rejected", question_id=str(question_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -- Memory consolidation


@router.post("/memory/consolidate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_memory_consolidation(
    user_id: uuid.UUID,
    _admin: CurrentAdmin,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Manually trigger Batch API memory consolidation for a user."""
    from app.config import settings as cfg
    from app.models.user_memory import UserMemory
    from app.services.memory.builder import consolidate_memory

    result = await db.execute(select(UserMemory).where(UserMemory.user_id == user_id))
    memory = result.scalar_one_or_none()
    if memory is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No memory found for user."
        )

    submitted = await consolidate_memory(db, user_id, cfg.anthropic_api_key)
    return {
        "submitted": submitted,
        "batch_job_id": memory.batch_job_id,
        "message": "Job submitted." if submitted else "Already pending or nothing to consolidate.",
    }
