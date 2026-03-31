"""Tests for resume → session pre-fill (P1-C)."""

from __future__ import annotations

from app.services.voice.prompts import build_candidate_context_block, get_system_prompt

# ── build_candidate_context_block ─────────────────────────────────────────────


def test_context_block_with_full_resume() -> None:
    resume = {
        "current_role": "Senior Software Engineer",
        "target_level": "L6",
        "experience_years": 8,
        "skills": ["Python", "Go", "Kubernetes", "PostgreSQL", "Redis"],
        "experience_summary": "Backend engineer focused on distributed systems at scale.",
    }
    block = build_candidate_context_block(resume)
    assert "CANDIDATE BACKGROUND" in block
    assert "Senior Software Engineer" in block
    assert "L6" in block
    assert "8 years" in block
    assert "Python" in block
    assert "distributed systems" in block


def test_context_block_empty_resume() -> None:
    block = build_candidate_context_block({})
    assert block == ""


def test_context_block_none_resume() -> None:
    block = build_candidate_context_block(None)  # type: ignore[arg-type]
    assert block == ""


def test_context_block_partial_resume() -> None:
    resume = {"current_role": "Data Scientist", "skills": ["Python", "PyTorch"]}
    block = build_candidate_context_block(resume)
    assert "Data Scientist" in block
    assert "Python" in block
    # Missing fields should not cause errors
    assert "None" not in block


def test_context_block_caps_skills_at_12() -> None:
    resume = {"skills": [f"skill_{i}" for i in range(20)]}
    block = build_candidate_context_block(resume)
    # Only first 12 skills should appear
    assert "skill_11" in block
    assert "skill_12" not in block


# ── get_system_prompt integration ─────────────────────────────────────────────


def test_system_prompt_injects_candidate_context() -> None:
    context = "\nCANDIDATE BACKGROUND:\n- Current role: Staff Engineer\n"
    prompt = get_system_prompt(
        "behavioral",
        persona="neutral",
        candidate_context=context,
    )
    assert "Staff Engineer" in prompt


def test_system_prompt_without_context_unchanged() -> None:
    prompt_with = get_system_prompt("behavioral", candidate_context=None)
    prompt_without = get_system_prompt("behavioral")
    assert prompt_with == prompt_without


def test_system_prompt_context_present_in_all_session_types() -> None:
    context = "\nCANDIDATE BACKGROUND:\n- Current role: ML Engineer\n"
    for session_type in ("behavioral", "system_design", "coding_discussion", "diagnostic"):
        prompt = get_system_prompt(session_type, candidate_context=context)
        assert "ML Engineer" in prompt, f"Context missing from {session_type} prompt"
