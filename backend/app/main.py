"""InterviewCraft — FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated
import typing

import structlog
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.companies import router as companies_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.digest import router as digest_router
from app.api.v1.negotiation import router as negotiation_router
from app.api.v1.portfolio import router as portfolio_router
from app.api.v1.profile import router as profile_router
from app.api.v1.questions import router as questions_router
from app.api.v1.resume import router as resume_router
from app.api.v1.rewind import router as rewind_router
from app.api.v1.scoring import router as scoring_router
from app.api.v1.sessions import router as sessions_router
from app.api.v1.settings import router as settings_router
from app.api.v1.share import router as share_router
from app.api.v1.skills import router as skills_router
from app.api.v1.stories import router as stories_router
from app.config import settings
from app.database import get_db
from app.logging import configure_logging
from app.redis_client import close_redis

configure_logging()

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — startup and shutdown hooks."""
    logger.info("interviewcraft.startup", env=settings.app_env, debug=settings.debug)
    yield
    await close_redis()
    logger.info("interviewcraft.shutdown")


app = FastAPI(
    title="InterviewCraft API",
    version="0.1.0",
    description="Deliberate Practice Engine for Interviews",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(scoring_router)
app.include_router(skills_router)
app.include_router(rewind_router)
app.include_router(questions_router)
app.include_router(stories_router)
app.include_router(negotiation_router)
app.include_router(dashboard_router)
app.include_router(admin_router)
app.include_router(portfolio_router)
app.include_router(profile_router)
app.include_router(resume_router)
app.include_router(settings_router)
app.include_router(digest_router)
app.include_router(share_router)
app.include_router(companies_router)


@app.get("/health", tags=["ops"])
async def health_check(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, typing.Any]:
    """Readiness probe — checks process is up AND database is reachable.

    Used by Docker healthcheck, Railway/Fly.io, and load balancers.
    Returns 200 when ready; 503 if DB is unreachable.
    """
    from fastapi import HTTPException, status

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("health.db_unreachable", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unreachable",
        )
    return {"status": "ok", "version": "0.1.0"}
