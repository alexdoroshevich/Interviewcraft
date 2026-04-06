"""Share Card API — generate and retrieve public readiness snapshots.

POST /api/v1/share/card        — generate a card (authenticated)
GET  /api/v1/share/card/{token} — retrieve a card (public, no auth)
"""

from __future__ import annotations

import secrets
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.interview_session import InterviewSession, SessionStatus
from app.models.share_card import ShareCard
from app.models.skill_graph_node import SkillGraphNode
from app.schemas.share import ShareCardCreateResponse, ShareCardPublicResponse, ShareCardSnapshot
from app.services.auth.dependencies import CurrentUser

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/share", tags=["share"])

_SHARE_TTL_DAYS = 30


@router.post("/card", response_model=ShareCardCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_share_card(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShareCardCreateResponse:
    """Generate a shareable readiness card snapshot for the current user."""
    uid = current_user.id

    # ── Skills ─────────────────────────────────────────────────────────────────
    skills_result = await db.execute(select(SkillGraphNode).where(SkillGraphNode.user_id == uid))
    nodes = list(skills_result.scalars().all())

    if not nodes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Complete at least one scored session before sharing.",
        )

    # ── Session count ──────────────────────────────────────────────────────────
    sessions_result = await db.execute(
        select(func.count(InterviewSession.id)).where(
            InterviewSession.user_id == uid,
            InterviewSession.status == SessionStatus.COMPLETED,
        )
    )
    session_count: int = sessions_result.scalar_one()

    # ── Compute snapshot ───────────────────────────────────────────────────────
    cat_buckets: dict[str, list[int]] = defaultdict(list)
    for n in nodes:
        cat_buckets[n.skill_category].append(n.current_score)
    skill_scores_by_category = {
        cat: round(sum(scores) / len(scores), 1) for cat, scores in cat_buckets.items()
    }

    avg_skill = round(sum(n.current_score for n in nodes) / len(nodes), 1)

    top_nodes = sorted(nodes, key=lambda n: n.current_score, reverse=True)[:3]
    top_strengths = [n.skill_name.replace("_", " ").title() for n in top_nodes]

    # Same readiness formula as dashboard
    session_signal = min(30, session_count * 3)
    readiness = min(100, int(avg_skill * 0.6 + session_signal))

    snapshot = ShareCardSnapshot(
        readiness_score=readiness,
        avg_skill_score=avg_skill,
        skill_scores_by_category=skill_scores_by_category,
        top_strengths=top_strengths,
        session_count=session_count,
        generated_at=datetime.now(UTC).isoformat(),
    )

    expires_at = datetime.now(UTC) + timedelta(days=_SHARE_TTL_DAYS)

    card = ShareCard(
        user_id=uid,
        token=secrets.token_urlsafe(24),
        snapshot_data=snapshot.model_dump(),
        expires_at=expires_at,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)

    logger.info("share_card.created", user_id=str(uid), token=card.token[:8])

    return ShareCardCreateResponse(
        token=card.token,
        share_url=f"/share/{card.token}",
        expires_at=expires_at.isoformat(),
    )


@router.get("/card/{token}", response_model=ShareCardPublicResponse)
async def get_share_card(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ShareCardPublicResponse:
    """Retrieve a public share card by token. No authentication required."""
    result = await db.execute(select(ShareCard).where(ShareCard.token == token))
    card = result.scalar_one_or_none()

    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found.")

    if card.expires_at and card.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card has expired.")

    return ShareCardPublicResponse(
        token=card.token,
        snapshot=ShareCardSnapshot(**card.snapshot_data),
        created_at=card.created_at.isoformat(),
        expires_at=card.expires_at.isoformat() if card.expires_at else None,
    )
