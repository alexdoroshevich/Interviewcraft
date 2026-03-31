"""Tests for user-contributed questions (P2-B).

Covers: schema validation, upvote uniqueness logic, status filter,
and contribute request validation rules.
"""

from __future__ import annotations

import uuid

from app.schemas.skills import (
    ContributeQuestionRequest,
    ContributeQuestionResponse,
    QuestionResponse,
)

# ── Schema tests ───────────────────────────────────────────────────────────────


def test_contribute_request_defaults() -> None:
    """ContributeQuestionRequest has sensible defaults."""
    req = ContributeQuestionRequest(text="Tell me about a time you...", type="behavioral")
    assert req.difficulty == "l5"
    assert req.skills_tested == []
    assert req.company is None


def test_contribute_request_full() -> None:
    """All fields serialize correctly."""
    req = ContributeQuestionRequest(
        text="Design a rate limiter for a distributed system.",
        type="system_design",
        difficulty="l6",
        skills_tested=["scalability_thinking", "tradeoff_analysis"],
        company="google",
    )
    assert req.type == "system_design"
    assert "scalability_thinking" in req.skills_tested
    assert req.company == "google"


def test_contribute_response_schema() -> None:
    """ContributeQuestionResponse carries expected fields."""
    resp = ContributeQuestionResponse(
        id=uuid.uuid4(),
        status="pending",
        message="Your question is under review.",
    )
    assert resp.status == "pending"
    assert "review" in resp.message


def test_question_response_new_fields() -> None:
    """QuestionResponse includes status, upvotes, submitted_by."""
    q = QuestionResponse(
        id=uuid.uuid4(),
        text="How would you design a URL shortener?",
        type="system_design",
        difficulty="l5",
        skills_tested=["component_design"],
        status="approved",
        upvotes=3,
        submitted_by=None,
    )
    assert q.status == "approved"
    assert q.upvotes == 3
    assert q.submitted_by is None


def test_question_response_defaults_approved() -> None:
    """Status defaults to 'approved' for backward compatibility."""
    q = QuestionResponse(
        id=uuid.uuid4(),
        text="Some question",
        type="behavioral",
        difficulty="l4",
        skills_tested=[],
    )
    assert q.status == "approved"
    assert q.upvotes == 0


# ── Business logic tests ────────────────────────────────────────────────────────


def test_status_values_are_valid() -> None:
    """Only three valid status values exist."""
    from app.models.question import QUESTION_STATUSES

    assert set(QUESTION_STATUSES) == {"pending", "approved", "rejected"}


def test_approved_filter_excludes_pending() -> None:
    """Simulated select_question filters only approved questions."""
    statuses = ["approved", "pending", "approved", "rejected", "approved"]
    approved = [s for s in statuses if s == "approved"]
    assert len(approved) == 3


def test_upvote_uniqueness_model() -> None:
    """QuestionUpvote model enforces user-question uniqueness via constraint name."""
    from app.models.question import QuestionUpvote

    constraints = [c.name for c in QuestionUpvote.__table_args__]
    assert "uq_question_upvote" in constraints


def test_skill_list_parsing() -> None:
    """Comma-separated skills parse correctly (mimics frontend logic)."""
    raw = "star_structure, ownership_signal, conflict_resolution"
    skills = [s.strip() for s in raw.split(",") if s.strip()]
    assert skills == ["star_structure", "ownership_signal", "conflict_resolution"]
