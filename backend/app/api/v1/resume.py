"""Resume upload and profile endpoints.

POST /upload  — parse PDF/DOCX, extract structured profile via Claude Haiku
GET  /profile — return stored profile
PUT  /profile — manually update profile fields
"""

import io
import json
import time
import typing
from typing import Annotated

import structlog
from anthropic import AsyncAnthropic
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.usage_log import UsageLog
from app.models.user import User
from app.schemas.resume import (
    ResumeProfile,
    ResumeProfileResponse,
    ResumeProfileUpdate,
    ResumeUploadResponse,
)
from app.services.auth.dependencies import CurrentUser
from app.services.voice.costs import calc_anthropic_cost

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/resume", tags=["resume"])

_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
_ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract text from a PDF file using PyPDF2."""
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except ImportError:
        logger.warning("resume.pdf_pypdf2_unavailable", fallback="raw_decode")
        # Fallback: decode raw bytes (won't work well but avoids crash)
        return file_bytes.decode("utf-8", errors="ignore")
    except Exception as exc:
        logger.error("resume.pdf_extraction_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Failed to extract text from PDF: {exc}",
        )


def _extract_text_from_docx(file_bytes: bytes) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        paragraphs: list[str] = []
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text.strip())
        return "\n".join(paragraphs)
    except ImportError:
        logger.error("resume.docx_library_unavailable")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="DOCX parsing not available — python-docx not installed",
        )
    except Exception as exc:
        logger.error("resume.docx_extraction_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Failed to extract text from DOCX: {exc}",
        )


async def _parse_resume_with_claude(
    resume_text: str, user: User, db: AsyncSession
) -> dict[str, typing.Any]:
    """Call Claude Haiku to extract structured profile from resume text."""
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API key not configured",
        )

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Analyze this resume text and extract structured data. Return ONLY valid JSON with these fields:
- experience_years: integer (total years of professional experience, estimate if not explicit)
- current_role: string (most recent job title)
- target_role: string (infer from experience trajectory, or use current role)
- target_level: string (one of "L3", "L4", "L5", "L6", "L7" — estimate based on experience)
- target_company: string or null (if mentioned in objective/summary)
- skills: list of strings (technical skills, programming languages, frameworks)
- projects: list of objects with "title", "description", "impact" fields (top 3-5 notable projects)
- experience_summary: string (2-3 sentence professional summary)

Resume text:
{resume_text[:8000]}"""

    start_ms = time.monotonic_ns() // 1_000_000

    try:
        response = await client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:
        logger.error("resume.claude_call_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to parse resume with AI",
        )

    latency_ms = (time.monotonic_ns() // 1_000_000) - start_ms
    first_block = response.content[0]
    from anthropic.types import TextBlock

    if not isinstance(first_block, TextBlock):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unexpected response format from AI",
        )
    raw_text = first_block.text

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    cost_usd = calc_anthropic_cost("claude-haiku-4-5", input_tokens, output_tokens)

    # Log usage
    usage_log = UsageLog(
        user_id=user.id,
        provider="anthropic",
        operation="resume_parse",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        latency_ms=latency_ms,
        cached=False,
    )
    db.add(usage_log)

    logger.info(
        "resume.claude_parse_complete",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=float(cost_usd),
        latency_ms=latency_ms,
    )

    # Parse JSON from response
    try:
        # Strip markdown code fences if present
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[: cleaned.rfind("```")]
        parsed = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        logger.error("resume.json_parse_failed", raw_length=len(raw_text))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned invalid JSON — please try again",
        )

    return parsed if isinstance(parsed, dict) else {}


# ── POST /upload ──────────────────────────────────────────────────────────────


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> ResumeUploadResponse:
    """Upload a PDF or DOCX resume, parse it, and store structured profile."""
    # Validate file extension
    filename = file.filename or ""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()

    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}",
        )

    # Read and validate size
    file_bytes = await file.read()
    if len(file_bytes) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {_MAX_FILE_SIZE // (1024 * 1024)} MB",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    logger.info("resume.upload_started", ext=ext, size_bytes=len(file_bytes))

    # Extract text
    if ext == ".pdf":
        resume_text = _extract_text_from_pdf(file_bytes)
    else:
        resume_text = _extract_text_from_docx(file_bytes)

    if not resume_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Could not extract any text from the uploaded file",
        )

    # Parse with Claude
    profile_data = await _parse_resume_with_claude(resume_text, user, db)

    # Store in user record (merge, don't overwrite — preserve self_assessment etc.)
    existing_profile = dict(user.profile) if user.profile else {}
    existing_profile["resume"] = profile_data
    user.profile = existing_profile
    user.resume_text = resume_text[:50000]  # Cap at 50k chars
    await db.commit()
    await db.refresh(user)

    logger.info("resume.upload_complete", user_id=str(user.id))

    return ResumeUploadResponse(
        message="Resume parsed successfully",
        profile=ResumeProfile(**profile_data),
    )


# ── GET /profile ──────────────────────────────────────────────────────────────


@router.get("/profile", response_model=ResumeProfileResponse)
async def get_profile(
    user: CurrentUser,
) -> ResumeProfileResponse:
    """Return the user's stored profile data."""
    profile = user.profile or {}
    resume_data = profile.get("resume")
    if resume_data is None:
        return ResumeProfileResponse(profile=None, has_resume=False)

    return ResumeProfileResponse(
        profile=ResumeProfile(**resume_data),
        has_resume=user.resume_text is not None,
    )


# ── PUT /profile ──────────────────────────────────────────────────────────────


@router.put("/profile", response_model=ResumeProfileResponse)
async def update_profile(
    body: ResumeProfileUpdate,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResumeProfileResponse:
    """Manually update profile fields (merge with existing data)."""
    existing = dict(user.profile) if user.profile else {}
    resume_data = existing.get("resume", {})

    # Merge only non-None fields from the request
    update_data = body.model_dump(exclude_none=True)
    resume_data.update(update_data)
    existing["resume"] = resume_data

    user.profile = existing
    await db.commit()
    await db.refresh(user)

    logger.info("resume.profile_updated", user_id=str(user.id), fields=list(update_data.keys()))

    return ResumeProfileResponse(
        profile=ResumeProfile(**resume_data),
        has_resume=user.resume_text is not None,
    )
