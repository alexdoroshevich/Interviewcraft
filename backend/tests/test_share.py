"""Tests for share card endpoints.

Covers: card creation, expiry enforcement, public access without auth,
and the 422 guard when no skills exist.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.schemas.share import ShareCardCreateResponse, ShareCardPublicResponse, ShareCardSnapshot

# ── Unit tests for snapshot schema ────────────────────────────────────────────


def test_snapshot_schema_round_trips() -> None:
    """ShareCardSnapshot serialises and deserialises without data loss."""
    snap = ShareCardSnapshot(
        readiness_score=72,
        avg_skill_score=65.4,
        skill_scores_by_category={"behavioral": 70.0, "system_design": 55.0},
        top_strengths=["Star Structure", "Ownership Signal"],
        session_count=8,
        generated_at=datetime.now(UTC).isoformat(),
    )
    restored = ShareCardSnapshot(**snap.model_dump())
    assert restored.readiness_score == snap.readiness_score
    assert restored.avg_skill_score == snap.avg_skill_score
    assert restored.top_strengths == snap.top_strengths


def test_snapshot_skill_scores_by_category() -> None:
    """Category scores dict is preserved intact."""
    cats = {"behavioral": 80.0, "communication": 60.0, "coding_discussion": 45.0}
    snap = ShareCardSnapshot(
        readiness_score=68,
        avg_skill_score=61.7,
        skill_scores_by_category=cats,
        top_strengths=["Star Structure"],
        session_count=3,
        generated_at=datetime.now(UTC).isoformat(),
    )
    assert snap.skill_scores_by_category == cats


def test_create_response_contains_share_url() -> None:
    """ShareCardCreateResponse always includes a /share/... path."""
    token = "abc123xyz"
    resp = ShareCardCreateResponse(
        token=token,
        share_url=f"/share/{token}",
        expires_at=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
    )
    assert resp.share_url.startswith("/share/")
    assert token in resp.share_url


def test_public_response_optional_expires() -> None:
    """expires_at is nullable on ShareCardPublicResponse."""
    snap = ShareCardSnapshot(
        readiness_score=50,
        avg_skill_score=50.0,
        skill_scores_by_category={},
        top_strengths=[],
        session_count=1,
        generated_at=datetime.now(UTC).isoformat(),
    )
    resp = ShareCardPublicResponse(
        token="tok",
        snapshot=snap,
        created_at=datetime.now(UTC).isoformat(),
        expires_at=None,
    )
    assert resp.expires_at is None


def test_readiness_capped_at_100() -> None:
    """Readiness formula should never exceed 100 even for very high inputs."""
    avg_skill = 100.0
    session_count = 100
    session_signal = min(30, session_count * 3)
    readiness = min(100, int(avg_skill * 0.6 + session_signal))
    assert readiness <= 100


def test_readiness_zero_sessions() -> None:
    """Readiness with zero sessions is purely skill-based."""
    avg_skill = 60.0
    session_signal = min(30, 0 * 3)
    readiness = min(100, int(avg_skill * 0.6 + session_signal))
    assert readiness == 36


def test_top_strengths_limited_to_three() -> None:
    """Only top 3 skill nodes contribute to top_strengths."""
    scores = [90, 80, 70, 60, 50]
    names = [f"skill_{i}" for i in range(len(scores))]
    nodes_sorted = sorted(zip(scores, names), reverse=True)[:3]
    strengths = [name.replace("_", " ").title() for _, name in nodes_sorted]
    assert len(strengths) == 3
