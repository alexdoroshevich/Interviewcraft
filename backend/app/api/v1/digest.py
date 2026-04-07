"""Weekly digest endpoints.

  GET  /api/v1/digest/preview  — returns digest HTML for current user (no email sent)
  POST /api/v1/digest/send     — sends digest email to current user immediately

Admin-only:
  POST /api/v1/digest/send-all — send digest to all opted-in users (background task)
"""

from __future__ import annotations

import typing
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings as app_settings
from app.database import get_db
from app.models.interview_session import InterviewSession
from app.models.segment_score import SegmentScore
from app.models.skill_graph_node import SkillGraphNode
from app.models.user import User
from app.services.auth.dependencies import CurrentAdmin, CurrentUser
from app.services.email import DigestStats, build_digest_html, send_email

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/digest", tags=["digest"])

_APP_URL = "http://localhost:3000"  # overridden by CORS_ORIGINS[0] if available
_SETTINGS_KEY = "app_settings"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _email_digest_enabled(user: User) -> bool:
    """Return True if user has opted into weekly digest emails."""
    profile_settings = (user.profile or {}).get(_SETTINGS_KEY, {})
    return bool(profile_settings.get("email_digest", False))


async def _build_stats(user: User, db: AsyncSession) -> DigestStats:
    """Query DB and assemble DigestStats for a user."""
    now = datetime.now(tz=UTC)
    week_ago = now - timedelta(days=7)

    # Sessions this week (completed)
    sessions_q = await db.execute(
        select(InterviewSession)
        .where(
            InterviewSession.user_id == user.id,
            InterviewSession.status == "completed",
        )
        .order_by(InterviewSession.created_at.desc())
    )
    all_sessions = list(sessions_q.scalars().all())
    sessions_this_week = [s for s in all_sessions if s.created_at >= week_ago]

    # Avg scores from segment_scores for recent sessions
    avg_this_week: float | None = None
    avg_all_time: float | None = None

    session_ids_week = [s.id for s in sessions_this_week]
    session_ids_all = [s.id for s in all_sessions]

    async def _avg_score(session_ids: list[uuid.UUID]) -> float | None:
        if not session_ids:
            return None
        scores_q = await db.execute(
            select(SegmentScore.overall_score).where(
                SegmentScore.session_id.in_(session_ids),
                SegmentScore.overall_score.isnot(None),
            )
        )
        scores = [r for r in scores_q.scalars().all() if r is not None]
        return sum(scores) / len(scores) if scores else None

    avg_this_week = await _avg_score(session_ids_week)
    avg_all_time = await _avg_score(session_ids_all)

    # Skill weaknesses — bottom 3 by current_score (only nodes with evidence)
    skills_q = await db.execute(
        select(SkillGraphNode)
        .where(SkillGraphNode.user_id == user.id)
        .order_by(SkillGraphNode.current_score.asc())
    )
    skill_nodes = list(skills_q.scalars().all())
    # Only include skills with at least one evidence link
    weak_nodes = [n for n in skill_nodes if n.evidence_links][:3]
    top_weaknesses = [(n.skill_name, n.current_score) for n in weak_nodes]

    # Due for review
    due_nodes = [
        n for n in skill_nodes if n.next_review_due is not None and n.next_review_due <= now
    ]
    due_for_review = [n.skill_name for n in due_nodes]

    return DigestStats(
        user_email=user.email,
        sessions_this_week=len(sessions_this_week),
        sessions_total=len(all_sessions),
        avg_score_this_week=avg_this_week,
        avg_score_all_time=avg_all_time,
        top_weaknesses=top_weaknesses,
        due_for_review=due_for_review,
        sessions_completed_total=len(all_sessions),
    )


def _app_url() -> str:
    origins = app_settings.cors_origins
    if origins:
        return origins[0].rstrip("/")
    return _APP_URL


# ── GET /api/v1/digest/preview ───────────────────────────────────────────────


@router.get("/preview", response_class=Response)
async def preview_digest(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Return the digest HTML for the current user without sending an email.

    Useful for previewing the digest in a browser.
    """
    stats = await _build_stats(current_user, db)
    html = build_digest_html(stats, app_url=_app_url())
    return Response(content=html, media_type="text/html")


# ── POST /api/v1/digest/send ──────────────────────────────────────────────────


@router.post("/send", status_code=status.HTTP_202_ACCEPTED)
async def send_digest_to_self(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, typing.Any]:
    """Send the weekly digest email to the current user immediately.

    Returns 202 whether SMTP is configured or not (check logs for delivery status).
    """
    stats = await _build_stats(current_user, db)
    html = build_digest_html(stats, app_url=_app_url())

    sent = await send_email(
        to_email=current_user.email,
        subject="Your weekly InterviewCraft practice digest",
        html_body=html,
        config=app_settings,
    )

    logger.info(
        "digest.sent_to_user",
        user_id=str(current_user.id),
        smtp_configured=bool(app_settings.smtp_host),
        delivered=sent,
    )

    return {
        "status": "queued" if sent else "skipped",
        "reason": None if sent else "SMTP not configured — set SMTP_HOST in .env",
    }


# ── POST /api/v1/digest/send-all (admin) ─────────────────────────────────────


async def _send_all_digests(db_url: str) -> None:
    """Background task: send digest to all opted-in users."""
    # Create a fresh DB session for the background task
    from app.database import AsyncSessionLocal  # local import to avoid circular dep

    async with AsyncSessionLocal() as db:
        users_q = await db.execute(select(User).where(User.is_active.is_(True)))
        users = list(users_q.scalars().all())

        sent = 0
        skipped = 0
        for user in users:
            if not _email_digest_enabled(user):
                skipped += 1
                continue
            stats = await _build_stats(user, db)
            html = build_digest_html(stats, app_url=_app_url())
            ok = await send_email(
                to_email=user.email,
                subject="Your weekly InterviewCraft practice digest",
                html_body=html,
                config=app_settings,
            )
            if ok:
                sent += 1
            else:
                skipped += 1

        logger.info("digest.send_all_complete", sent=sent, skipped=skipped, total=len(users))


@router.post("/send-all", status_code=status.HTTP_202_ACCEPTED)
async def send_all_digests(
    background_tasks: BackgroundTasks,
    admin: CurrentAdmin,
) -> dict[str, typing.Any]:
    """Admin: enqueue weekly digest send to all opted-in users.

    Runs asynchronously — returns immediately.
    """
    background_tasks.add_task(_send_all_digests, app_settings.database_url)
    logger.info("digest.send_all_enqueued", admin_id=str(admin.id))

    return {"status": "enqueued", "message": "Digest emails queued for all opted-in users"}
