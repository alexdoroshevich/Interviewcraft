"""Smoke tests for the JD analysis endpoint schema and validation."""

from __future__ import annotations

import pytest

from app.schemas.session import JdAnalysisRequest, JdAnalysisResponse, JdFocusArea


def test_jd_request_rejects_too_short() -> None:
    with pytest.raises(Exception):
        JdAnalysisRequest(jd_text="short")


def test_jd_request_rejects_too_long() -> None:
    with pytest.raises(Exception):
        JdAnalysisRequest(jd_text="x" * 8001)


def test_jd_request_accepts_valid() -> None:
    req = JdAnalysisRequest(jd_text="We are looking for a senior backend engineer " * 5)
    assert len(req.jd_text) >= 50


def test_jd_response_builds_correctly() -> None:
    resp = JdAnalysisResponse(
        skills_required=["Python", "FastAPI", "PostgreSQL"],
        skills_nice_to_have=["Redis", "Kubernetes"],
        seniority="senior",
        role_type="backend",
        suggested_session_type="system_design",
        suggested_company="google",
        focus_areas=[
            JdFocusArea(area="Distributed systems", reason="Core to the role", priority="high"),
        ],
        coaching_note="Focus on large-scale system design examples.",
    )
    assert resp.seniority == "senior"
    assert resp.suggested_company == "google"
    assert len(resp.focus_areas) == 1
    assert resp.focus_areas[0].priority == "high"


def test_jd_response_allows_no_company() -> None:
    resp = JdAnalysisResponse(
        skills_required=["Java"],
        skills_nice_to_have=[],
        seniority="mid",
        role_type="backend",
        suggested_session_type="behavioral",
        suggested_company=None,
        focus_areas=[],
        coaching_note="",
    )
    assert resp.suggested_company is None
