"""Company Intel API — community-contributed interview insights.

GET  /api/v1/companies/{company}/intel      — list approved intel for a company
POST /api/v1/companies/{company}/intel      — submit new intel (authenticated)
POST /api/v1/companies/{company}/intel/{id}/upvote — upvote a tip
"""

from __future__ import annotations

import typing
import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.company_intel import CompanyIntel
from app.services.auth.dependencies import CurrentUser

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/companies", tags=["companies"])

_VALID_CATEGORIES = frozenset({"process", "technical", "culture", "tips"})
_MAX_CONTENT_LEN = 1000


# ── Schemas ───────────────────────────────────────────────────────────────────


class IntelSubmitRequest(BaseModel):
    """Body for POST /companies/{company}/intel."""

    category: str = Field(default="process")
    content: str = Field(min_length=20, max_length=_MAX_CONTENT_LEN)


class IntelResponse(BaseModel):
    """One company intel item."""

    id: uuid.UUID
    company: str
    category: str
    content: str
    upvotes: int
    created_at: str


class IntelListResponse(BaseModel):
    """Paginated list of intel items for a company."""

    company: str
    items: list[IntelResponse]
    total: int


# ── GET /{company}/intel ──────────────────────────────────────────────────────


@router.get("/{company}/intel", response_model=IntelListResponse)
async def list_company_intel(
    company: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0,
) -> IntelListResponse:
    """Return approved community intel for the given company.

    Public — no auth required. Sorted by upvotes descending.
    """
    company_lower = company.lower().strip()

    count_result = await db.execute(
        select(func.count(CompanyIntel.id)).where(
            CompanyIntel.company == company_lower,
            CompanyIntel.status == "approved",
        )
    )
    total = count_result.scalar_one()

    result = await db.execute(
        select(CompanyIntel)
        .where(CompanyIntel.company == company_lower, CompanyIntel.status == "approved")
        .order_by(CompanyIntel.upvotes.desc(), CompanyIntel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()

    return IntelListResponse(
        company=company_lower,
        items=[
            IntelResponse(
                id=item.id,
                company=item.company,
                category=item.category,
                content=item.content,
                upvotes=item.upvotes,
                created_at=item.created_at.isoformat(),
            )
            for item in items
        ],
        total=total,
    )


# ── POST /{company}/intel ─────────────────────────────────────────────────────


@router.post(
    "/{company}/intel",
    response_model=IntelResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_company_intel(
    company: str,
    body: IntelSubmitRequest,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IntelResponse:
    """Submit a new intel tip for a company.

    Tips are approved immediately (no moderation queue for MVP).
    Category must be one of: process, technical, culture, tips.
    """
    if body.category not in _VALID_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid category. Must be one of: {', '.join(sorted(_VALID_CATEGORIES))}",
        )

    company_lower = company.lower().strip()

    intel = CompanyIntel(
        user_id=current_user.id,
        company=company_lower,
        category=body.category,
        content=body.content.strip(),
        status="approved",
    )
    db.add(intel)
    await db.commit()
    await db.refresh(intel)

    logger.info(
        "company_intel.submitted",
        user_id=str(current_user.id),
        company=company_lower,
        category=body.category,
    )

    return IntelResponse(
        id=intel.id,
        company=intel.company,
        category=intel.category,
        content=intel.content,
        upvotes=intel.upvotes,
        created_at=intel.created_at.isoformat(),
    )


# ── POST /{company}/intel/{id}/upvote ─────────────────────────────────────────


@router.post("/{company}/intel/{intel_id}/upvote", status_code=status.HTTP_200_OK)
async def upvote_intel(
    company: str,
    intel_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, typing.Any]:
    """Increment the upvote count on an intel item."""
    result = await db.execute(
        select(CompanyIntel).where(
            CompanyIntel.id == intel_id,
            CompanyIntel.company == company.lower().strip(),
            CompanyIntel.status == "approved",
        )
    )
    intel = result.scalar_one_or_none()

    if intel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intel not found")

    intel.upvotes += 1
    await db.commit()

    logger.info(
        "company_intel.upvoted",
        intel_id=str(intel_id),
        new_count=intel.upvotes,
    )
    return {"upvotes": intel.upvotes}
