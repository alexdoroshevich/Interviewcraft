"""Pydantic schemas for resume upload and profile endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class ProjectItem(BaseModel):
    title: str
    description: str
    impact: str = ""


class ResumeProfile(BaseModel):
    """Structured profile data extracted from a resume."""

    experience_years: int | None = None
    current_role: str | None = None
    target_role: str | None = None
    target_level: str | None = Field(None, description="L3-L7 or equivalent")
    target_company: str | None = None
    skills: list[str] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    experience_summary: str | None = Field(None, description="2-3 sentence summary of experience")


class ResumeUploadResponse(BaseModel):
    """Response after uploading and parsing a resume."""

    message: str
    profile: ResumeProfile

    model_config = {"from_attributes": True}


class ResumeProfileResponse(BaseModel):
    """Response for GET /profile — returns stored profile data."""

    profile: ResumeProfile | None = None
    has_resume: bool

    model_config = {"from_attributes": True}


class ResumeProfileUpdate(BaseModel):
    """Request body for PUT /profile — manually update profile fields."""

    experience_years: int | None = None
    current_role: str | None = None
    target_role: str | None = None
    target_level: str | None = None
    target_company: str | None = None
    skills: list[str] | None = None
    projects: list[dict[str, Any]] | None = None
    experience_summary: str | None = None
