"""Recall benchmark for the InterviewCraft user memory system.

Standalone evaluation script. Does not touch the DB or FastAPI.
Run from the repo root:
    python benchmarks/memory-recall/run.py --confirm

Pass --confirm to execute API calls (~$0.019). Without --confirm, only the
cost estimate is printed and the script exits cleanly.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import structlog

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
    load_dotenv(REPO_ROOT / ".env", override=False)  # fallback to root .env
except ImportError:
    pass

logging.basicConfig(format="%(message)s", level=logging.INFO, stream=sys.stdout)
structlog.configure(
    processors=[structlog.processors.KeyValueRenderer(key_order=["event"], drop_missing=True)],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)
log = structlog.get_logger("memory_benchmark")

from anthropic import Anthropic  # noqa: E402

from app.services.memory.loader import (  # noqa: E402
    _bootstrap_from_skills,
    _format_memory_block,
)

HAIKU_MODEL = "claude-haiku-4-5"
HAIKU_INPUT_PER_TOKEN = 1.0 / 1_000_000
HAIKU_OUTPUT_PER_TOKEN = 5.0 / 1_000_000

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Rough estimate: 40 questions x ~500 input tokens x $1/MTok + ~25 output x $5/MTok
ESTIMATED_COST_USD = 0.019


def emit(msg: str) -> None:
    """Emit a human-readable line via structlog."""
    log.info(msg)


def build_user_a_doc() -> dict[str, Any]:
    """User A: 8 sessions, 3 weak skills with mistakes, 2 strong, 3 stories."""
    return {
        "total_sessions": 8,
        "avg_score": 64,
        "target_role": "Senior Backend Engineer",
        "target_level": "L5",
        "target_companies": ["Stripe", "Datadog"],
        "career_goal": "Move from monolith team to distributed systems org within 12 months",
        "weakest_skills": [
            {
                "skill": "capacity_estimation",
                "score": 41,
                "trend": "declining",
                "top_mistake": "Confuses QPS with concurrent connections",
                "sessions_practiced": 4,
            },
            {
                "skill": "quantifiable_results",
                "score": 48,
                "trend": "stable",
                "top_mistake": "States significantly improved without a percentage",
                "sessions_practiced": 5,
            },
            {
                "skill": "tradeoff_analysis",
                "score": 52,
                "trend": "improving",
                "top_mistake": "Picks a solution before naming alternatives",
                "sessions_practiced": 3,
            },
        ],
        "strongest_skills": [
            {
                "skill": "api_design",
                "score": 82,
                "trend": "stable",
                "top_mistake": None,
                "sessions_practiced": 6,
            },
            {
                "skill": "ownership_signal",
                "score": 78,
                "trend": "improving",
                "top_mistake": None,
                "sessions_practiced": 4,
            },
        ],
        "recurring_mistakes": [
            "Jumps to implementation before clarifying requirements",
            "Drops the Result section of STAR under time pressure",
            "Uses passive voice when describing own contributions",
        ],
        "best_stories": [
            {
                "title": "Payment retry queue migration",
                "best_score": 84,
                "competencies": ["ownership", "tradeoffs", "impact"],
                "tip": "Lead with the 12% revenue-recovery number next time",
            },
            {
                "title": "Oncall incident root cause",
                "best_score": 76,
                "competencies": ["debugging", "communication"],
                "tip": "Name the specific Kafka lag metric you alerted on",
            },
            {
                "title": "Mentoring new SRE hire",
                "best_score": 71,
                "competencies": ["mentoring", "ownership"],
                "tip": None,
            },
        ],
        "communication_notes": [
            "Fast pacing under pressure -- fills silence with um and like",
            "Strong when using diagrams verbally; weaker when asked to recap without one",
        ],
        "coaching_insights": [
            {"insight": "Direct challenge on numbers produces stronger retries", "evidence_count": 3},
        ],
        "current_focus": "Practice capacity estimation with storage math",
    }


def build_user_b_doc() -> dict[str, Any]:
    """User B: 25 sessions, rich history, Google L5 target, avg 71."""
    return {
        "total_sessions": 25,
        "avg_score": 71,
        "target_role": "Staff Product Manager",
        "target_level": "L5",
        "target_companies": ["Google"],
        "career_goal": "Land Google L5 PM role by Q3 2026",
        "weakest_skills": [
            {
                "skill": "conflict_resolution",
                "score": 58,
                "trend": "stable",
                "top_mistake": "Frames disagreements as binary wins/losses",
                "sessions_practiced": 7,
            },
            {
                "skill": "pacing",
                "score": 61,
                "trend": "declining",
                "top_mistake": "Runs long on context, short on outcome",
                "sessions_practiced": 9,
            },
        ],
        "strongest_skills": [
            {
                "skill": "leadership_stories",
                "score": 88,
                "trend": "improving",
                "top_mistake": None,
                "sessions_practiced": 14,
            },
            {
                "skill": "quantifiable_results",
                "score": 85,
                "trend": "stable",
                "top_mistake": None,
                "sessions_practiced": 12,
            },
        ],
        "recurring_mistakes": [
            "Uses we when the question asks about individual contribution",
            "Mentions frameworks by name (RICE, ICE) without applying them concretely",
        ],
        "best_stories": [
            {
                "title": "Launching Ads Auto-Bidder v2",
                "best_score": 92,
                "competencies": ["leadership", "data", "ambiguity"],
                "tip": "Lead with the 0M revenue lift, then context",
            },
            {
                "title": "Killing the Legacy Reports product",
                "best_score": 86,
                "competencies": ["judgment", "ownership"],
                "tip": "Be specific about which teams you aligned",
            },
        ],
        "communication_notes": [
            "Confident delivery but buries the headline in the third sentence",
            "Uses I think as a hedge -- drop it when stating data",
        ],
        "coaching_insights": [
            {"insight": "Asking for the metric twice forces specificity", "evidence_count": 6},
            {"insight": "STAR works best when interrupted at Action step", "evidence_count": 4},
        ],
        "current_focus": "Pacing drills -- 90-second max per answer",
    }


def build_user_c_skill_nodes() -> list[MagicMock]:
    """User C: 3 sessions (sparse). Only skill bootstrap data."""
    nodes: list[MagicMock] = []
    skill_data = [
        ("edge_cases", "coding_discussion", 44, "declining", ["Misses null input check"], 2),
        ("conciseness", "communication", 49, "stable", ["Answers average 3 minutes"], 3),
        ("complexity_analysis", "coding_discussion", 55, "improving", [], 2),
        ("component_design", "system_design", 57, "stable", [], 1),
        ("star_structure", "behavioral", 68, "improving", [], 2),
        ("api_design", "system_design", 72, "stable", [], 2),
        ("testing_approach", "coding_discussion", 74, "improving", [], 3),
        ("confidence_under_pressure", "communication", 79, "improving", [], 3),
    ]
    for name, category, score, trend, mistakes, sessions in skill_data:
        node = MagicMock()
        node.skill_name = name
        node.skill_category = category
        node.current_score = score
        node.trend = trend
        node.typical_mistakes = mistakes
        node.evidence_links = [{"session": f"s{i}"} for i in range(sessions)]
        nodes.append(node)
    return nodes


async def build_user_c_doc() -> dict[str, Any]:
    """Build User C doc via the real _bootstrap_from_skills with a mocked DB."""
    nodes = build_user_c_skill_nodes()
    skills_result = MagicMock()
    skills_result.scalars.return_value.all.return_value = nodes
    count_result = MagicMock()
    count_result.scalar.return_value = 3
    db = MagicMock()
    # _bootstrap_from_skills does a 3rd db.execute for the User lookup (resume/profile)
    user_result_mock = MagicMock()
    user_result_mock.scalar_one_or_none.return_value = None  # no user profile
    db.execute = AsyncMock(side_effect=[skills_result, count_result, user_result_mock])
    seed: dict[str, Any] = {"total_sessions": 3}
    doc = await _bootstrap_from_skills(db, uuid.uuid4(), seed)
    return doc


def build_user_d_doc() -> dict[str, Any]:
    """User D: edge case -- all skills near 50, no stories."""
    return {
        "total_sessions": 6,
        "avg_score": 50,
        "weakest_skills": [
            {"skill": "scalability_thinking", "score": 49, "trend": "stable", "top_mistake": None, "sessions_practiced": 2},
            {"skill": "filler_word_control", "score": 50, "trend": "stable", "top_mistake": None, "sessions_practiced": 3},
        ],
        "strongest_skills": [
            {"skill": "api_design", "score": 52, "trend": "stable", "top_mistake": None, "sessions_practiced": 2},
            {"skill": "star_structure", "score": 51, "trend": "stable", "top_mistake": None, "sessions_practiced": 3},
        ],
        "recurring_mistakes": [],
        "best_stories": [],
        "communication_notes": [],
        "coaching_insights": [],
    }


def build_user_e_doc() -> dict[str, Any]:
    """User E: 15 sessions, multiple recurring mistakes, specific comm patterns."""
    return {
        "total_sessions": 15,
        "avg_score": 67,
        "target_role": "Engineering Manager",
        "target_level": "M1",
        "target_companies": ["Meta", "Shopify"],
        "weakest_skills": [
            {
                "skill": "conciseness", "score": 47, "trend": "declining",
                "top_mistake": "Average answer length is 4.5 minutes", "sessions_practiced": 11,
            },
            {
                "skill": "counter_strategy", "score": 53, "trend": "stable",
                "top_mistake": "Accepts first counter-offer without exploring alternatives", "sessions_practiced": 4,
            },
        ],
        "strongest_skills": [
            {"skill": "mentoring_signal", "score": 81, "trend": "improving", "top_mistake": None, "sessions_practiced": 9},
        ],
        "recurring_mistakes": [
            "Starts every answer with So, basically",
            "Over-uses the word ecosystem -- 6+ times per session",
            "Forgets to close the loop on metrics by end of answer",
            "Apologizes for thinking out loud (sorry, still thinking)",
            "Tells stories in chronological order instead of impact-first",
        ],
        "best_stories": [
            {"title": "Promoting two reports to senior", "best_score": 79, "competencies": ["mentoring", "growth"], "tip": "Name the performance review criteria you used"},
            {"title": "Cross-team platform migration", "best_score": 74, "competencies": ["influence", "technical"], "tip": None},
        ],
        "communication_notes": [
            "Verbal tics: so, basically and ecosystem are overused",
            "Rambles when nervous -- pacing collapses after 90 seconds",
        ],
        "coaching_insights": [
            {"insight": "Hard time limit of 2 minutes per answer fixes pacing", "evidence_count": 5},
            {"insight": "Asking for the one number cuts the ramble", "evidence_count": 3},
        ],
        "current_focus": "Conciseness -- strict 90-second answer cap",
    }


@dataclass
class Question:
    qid: str
    user: str
    category: str
    question: str
    ground_truth: str
    must_contain: list[str] = field(default_factory=list)
    expect_not_in_context: bool = False


QUESTIONS: list[Question] = [
    # User A
    Question("A1", "A", "direct", "What is this candidate weakest skill and what score does it have?", "capacity_estimation, score 41", must_contain=["capacity_estimation", "41"]),
    Question("A2", "A", "numerical", "How many previous sessions has this candidate completed?", "8", must_contain=["8"]),
    Question("A3", "A", "direct", "What specific mistake does this candidate make with capacity estimation?", "Confuses QPS with concurrent connections", must_contain=["qps", "concurrent"]),
    Question("A4", "A", "multi_fact", "Which weak skill is currently improving?", "tradeoff_analysis", must_contain=["tradeoff"]),
    Question("A5", "A", "story", "What is the highest-scoring story and what score did it get?", "Payment retry queue migration, 84", must_contain=["payment retry", "84"]),
    Question("A6", "A", "communication", "What filler words does this candidate use under pressure?", "um and like", must_contain=["um", "like"]),
    Question("A7", "A", "negative", "Does this candidate have a story about founding a startup?", "NOT IN CONTEXT", expect_not_in_context=True),
    Question("A8", "A", "direct", "What companies is this candidate targeting?", "Stripe and Datadog", must_contain=["stripe", "datadog"]),
    # User B
    Question("B1", "B", "numerical", "What is this candidate average score across sessions?", "71", must_contain=["71"]),
    Question("B2", "B", "direct", "What specific role and level is this candidate targeting?", "Staff Product Manager, L5 at Google", must_contain=["product manager", "l5", "google"]),
    Question("B3", "B", "story", "What is the top story and what was its score?", "Launching Ads Auto-Bidder v2, 92", must_contain=["auto-bidder", "92"]),
    Question("B4", "B", "multi_fact", "Which weak skill is declining, not stable?", "pacing", must_contain=["pacing"]),
    Question("B5", "B", "communication", "What hedge phrase does this candidate overuse that should be dropped?", "I think", must_contain=["i think"]),
    Question("B6", "B", "direct", "What recurring mistake does this candidate make with the word we?", "Uses we when asked about individual contribution", must_contain=["we", "individual"]),
    Question("B7", "B", "negative", "What is this candidate target salary?", "NOT IN CONTEXT", expect_not_in_context=True),
    Question("B8", "B", "numerical", "How many coaching insights are recorded for this candidate?", "2", must_contain=["2"]),
    # User C (bootstrap-only)
    Question("C1", "C", "numerical", "How many sessions has this candidate completed?", "3", must_contain=["3"]),
    Question("C2", "C", "direct", "What is the weakest skill for this candidate and its score?", "edge_cases, 44", must_contain=["edge_cases", "44"]),
    Question("C3", "C", "direct", "What is the top mistake in edge_cases?", "Misses null input check", must_contain=["null"]),
    Question("C4", "C", "direct", "What is the strongest skill for this candidate?", "confidence_under_pressure, 79", must_contain=["confidence_under_pressure"]),
    Question("C5", "C", "negative", "What stories are available for this candidate?", "NOT IN CONTEXT", expect_not_in_context=True),
    Question("C6", "C", "negative", "What recurring mistakes have been recorded for this candidate?", "NOT IN CONTEXT", expect_not_in_context=True),
    Question("C7", "C", "multi_fact", "Which weak skill is improving?", "complexity_analysis", must_contain=["complexity_analysis"]),
    Question("C8", "C", "negative", "What is the candidate target company?", "NOT IN CONTEXT", expect_not_in_context=True),
    # User D (flat scores, no stories)
    Question("D1", "D", "numerical", "How many sessions has this candidate completed?", "6", must_contain=["6"]),
    Question("D2", "D", "numerical", "What is the average score?", "50", must_contain=["50"]),
    Question("D3", "D", "direct", "What is the weakest skill listed?", "scalability_thinking, 49", must_contain=["scalability_thinking"]),
    Question("D4", "D", "negative", "What stories does this candidate have?", "NOT IN CONTEXT", expect_not_in_context=True),
    Question("D5", "D", "negative", "What recurring mistakes are recorded?", "NOT IN CONTEXT", expect_not_in_context=True),
    Question("D6", "D", "negative", "What target role is this candidate pursuing?", "NOT IN CONTEXT", expect_not_in_context=True),
    Question("D7", "D", "direct", "What is the score of the strongest skill?", "52 (api_design)", must_contain=["52"]),
    Question("D8", "D", "negative", "What communication notes have been recorded?", "NOT IN CONTEXT", expect_not_in_context=True),
    # User E
    Question("E1", "E", "numerical", "How many sessions has this candidate completed?", "15", must_contain=["15"]),
    Question("E2", "E", "communication", "What verbal tic does this candidate start every answer with?", "So, basically", must_contain=["so, basically"]),
    Question("E3", "E", "direct", "What word does this candidate over-use (6+ times per session)?", "ecosystem", must_contain=["ecosystem"]),
    Question("E4", "E", "numerical", "What is the average answer length for this candidate?", "4.5 minutes", must_contain=["4.5"]),
    Question("E5", "E", "multi_fact", "Which weak skill is declining and what is its score?", "conciseness, 47", must_contain=["conciseness", "47"]),
    Question("E6", "E", "story", "What is the top story and its competencies?", "Promoting two reports to senior; mentoring, growth", must_contain=["promoting", "mentoring"]),
    Question("E7", "E", "direct", "What is the current focus for this candidate?", "Conciseness -- strict 90-second answer cap", must_contain=["conciseness", "90"]),
    Question("E8", "E", "negative", "Does this candidate have any recorded negotiation stories?", "NOT IN CONTEXT", expect_not_in_context=True),
]


NOT_IN_CONTEXT_PHRASES = [
    "not in context", "not mentioned", "not provided", "no information",
    "not specified", "not recorded", "no stories", "no recurring mistakes",
    "no target", "no communication notes", "does not have", "no mention",
    "no such", "is not listed", "are not listed", "is not included", "are not included",
]


def _said_not_in_context(answer: str) -> bool:
    a = answer.lower()
    return any(phrase in a for phrase in NOT_IN_CONTEXT_PHRASES)


def score_answer(q: Question, answer: str, memory_block: str) -> int:
    """Score an answer on the [-1, 0, 1, 2] scale."""
    a = answer.lower().strip()

    if q.expect_not_in_context:
        if _said_not_in_context(a):
            return 2
        block_lower = memory_block.lower()
        for tok in a.split():
            tok_clean = tok.strip(".,;:()").lower()
            if any(c.isdigit() for c in tok_clean) and tok_clean not in block_lower:
                return -1
        return 0

    hits = [kw for kw in q.must_contain if kw.lower() in a]
    if not hits:
        if _said_not_in_context(a):
            return 0
        if len(a) > 10 and any(c.isdigit() for c in a):
            return -1
        return 0
    if len(hits) == len(q.must_contain):
        return 2
    return 1


PROMPT_TEMPLATE = """You are answering factual questions about a coaching candidate based only on the memory context below.
Answer with the specific fact requested. If the information is not in the context, say "NOT IN CONTEXT".
Be concise -- one sentence maximum.

{memory_block}

Question: {question}"""


@dataclass
class RunResult:
    qid: str
    user: str
    category: str
    question: str
    ground_truth: str
    model_answer: str
    score: int
    input_tokens: int
    output_tokens: int
    latency_ms: int


def run_benchmark(
    client: Anthropic,
    memory_blocks: dict[str, str],
    questions: list[Question],
) -> list[RunResult]:
    """Run each question against Claude Haiku and score the response."""
    results: list[RunResult] = []
    for q in questions:
        block = memory_blocks[q.user]
        prompt = PROMPT_TEMPLATE.format(memory_block=block, question=q.question)
        t0 = time.monotonic()
        try:
            msg = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            log.error("api_error", qid=q.qid, error=str(exc))
            results.append(RunResult(
                qid=q.qid, user=q.user, category=q.category,
                question=q.question, ground_truth=q.ground_truth,
                model_answer=f"[ERROR: {exc}]", score=0,
                input_tokens=0, output_tokens=0, latency_ms=0,
            ))
            continue
        latency_ms = int((time.monotonic() - t0) * 1000)
        answer_parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        answer = " ".join(answer_parts).strip()
        score = score_answer(q, answer, block)
        results.append(RunResult(
            qid=q.qid, user=q.user, category=q.category,
            question=q.question, ground_truth=q.ground_truth,
            model_answer=answer, score=score,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
            latency_ms=latency_ms,
        ))
        marker = {2: "OK", 1: "PARTIAL", 0: "MISS", -1: "HALLUCINATION"}[score]
        emit(f"  [{marker:<14}] {q.qid} {q.category:<14} -> {answer[:120]}")
    return results


def summarize(results: list[RunResult]) -> dict[str, Any]:
    """Aggregate per-user, per-category, and overall recall rates."""
    def rate(items: list[RunResult], target: int) -> float:
        return round(sum(1 for r in items if r.score == target) / len(items), 3) if items else 0.0

    total = len(results)
    correct = sum(1 for r in results if r.score == 2)
    partial = sum(1 for r in results if r.score == 1)
    missed = sum(1 for r in results if r.score == 0)
    hallucinated = sum(1 for r in results if r.score == -1)

    per_user: dict[str, dict[str, Any]] = {}
    for user in sorted({r.user for r in results}):
        items = [r for r in results if r.user == user]
        per_user[user] = {
            "total": len(items), "recall": rate(items, 2), "partial": rate(items, 1),
            "miss": rate(items, 0), "hallucination": rate(items, -1),
            "avg_score": round(sum(r.score for r in items) / len(items), 3),
        }

    per_category: dict[str, dict[str, Any]] = {}
    for cat in sorted({r.category for r in results}):
        items = [r for r in results if r.category == cat]
        per_category[cat] = {
            "total": len(items), "recall": rate(items, 2), "partial": rate(items, 1),
            "miss": rate(items, 0), "hallucination": rate(items, -1),
            "avg_score": round(sum(r.score for r in items) / len(items), 3),
        }

    total_in = sum(r.input_tokens for r in results)
    total_out = sum(r.output_tokens for r in results)
    cost = total_in * HAIKU_INPUT_PER_TOKEN + total_out * HAIKU_OUTPUT_PER_TOKEN

    return {
        "totals": {
            "questions": total, "correct": correct, "partial": partial,
            "missed": missed, "hallucinated": hallucinated,
            "recall_rate": round(correct / total, 3) if total else 0.0,
            "partial_rate": round(partial / total, 3) if total else 0.0,
            "miss_rate": round(missed / total, 3) if total else 0.0,
            "hallucination_rate": round(hallucinated / total, 3) if total else 0.0,
            "avg_score_out_of_2": round(sum(r.score for r in results) / total, 3) if total else 0.0,
        },
        "per_user": per_user,
        "per_category": per_category,
        "cost": {"input_tokens": total_in, "output_tokens": total_out, "usd": round(cost, 6)},
        "latency_ms_avg": int(sum(r.latency_ms for r in results) / total) if total else 0,
    }


def write_report(memory_blocks: dict[str, str], results: list[RunResult], summary: dict[str, Any]) -> None:
    """Emit a human-readable benchmark report via structlog."""
    bar = "=" * 78
    emit("")
    emit(bar)
    emit("INTERVIEWCRAFT MEMORY SYSTEM -- RECALL BENCHMARK")
    emit(bar)
    emit("")
    emit("Memory block sizes:")
    for user, block in sorted(memory_blocks.items()):
        emit(f"  User {user}: {len(block):>6} chars | {len(block.splitlines()):>3} lines")
    emit("")
    emit("--- Totals ---")
    t = summary["totals"]
    emit(f"  Questions:        {t['questions']}")
    emit(f"  Correct (2):      {t['correct']:>3}   ({t['recall_rate']*100:.1f}%)")
    emit(f"  Partial (1):      {t['partial']:>3}   ({t['partial_rate']*100:.1f}%)")
    emit(f"  Missed  (0):      {t['missed']:>3}   ({t['miss_rate']*100:.1f}%)")
    emit(f"  Hallucinated(-1): {t['hallucinated']:>3}   ({t['hallucination_rate']*100:.1f}%)")
    emit(f"  Avg score /2:     {t['avg_score_out_of_2']}")
    emit("")
    emit("--- Per user ---")
    emit(f"  {'User':<6}{'N':<5}{'Recall':<10}{'Partial':<10}{'Miss':<10}{'Hallu':<10}{'Avg':<6}")
    for user, stats in summary["per_user"].items():
        emit(f"  {user:<6}{stats['total']:<5}{stats['recall']*100:>5.1f}%    {stats['partial']*100:>5.1f}%    {stats['miss']*100:>5.1f}%    {stats['hallucination']*100:>5.1f}%    {stats['avg_score']:<5}")
    emit("")
    emit("--- Per question category ---")
    emit(f"  {'Category':<16}{'N':<5}{'Recall':<10}{'Partial':<10}{'Miss':<10}{'Hallu':<10}{'Avg':<6}")
    for cat, stats in summary["per_category"].items():
        emit(f"  {cat:<16}{stats['total']:<5}{stats['recall']*100:>5.1f}%    {stats['partial']*100:>5.1f}%    {stats['miss']*100:>5.1f}%    {stats['hallucination']*100:>5.1f}%    {stats['avg_score']:<5}")
    emit("")
    emit("--- Cost ---")
    c = summary["cost"]
    emit(f"  Input tokens:  {c['input_tokens']:,}")
    emit(f"  Output tokens: {c['output_tokens']:,}")
    emit(f"  Total cost:    ${c['usd']:.6f}")
    emit(f"  Avg latency:   {summary['latency_ms_avg']} ms")
    emit("")
    emit("--- Failures (miss + hallucination) ---")
    for r in results:
        if r.score <= 0:
            tag = "MISS" if r.score == 0 else "HALLU"
            emit(f"  [{tag}] {r.qid} ({r.category})")
            emit(f"    Q: {r.question}")
            emit(f"    Expected: {r.ground_truth}")
            emit(f"    Got:      {r.model_answer[:200]}")
    emit(bar)
    emit("")


def main() -> int:
    """Run the full benchmark end-to-end."""
    parser = argparse.ArgumentParser(description="InterviewCraft memory recall benchmark")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help=f"Actually run API calls. Without this flag only the cost estimate (~${ESTIMATED_COST_USD:.3f}) is shown.",
    )
    args = parser.parse_args()

    if not args.confirm:
        emit(
            f"Estimated cost: ~${ESTIMATED_COST_USD:.3f} "
            f"({len(QUESTIONS)} questions x {HAIKU_MODEL})"
        )
        emit("Pass --confirm to proceed.")
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("missing_api_key", hint="set ANTHROPIC_API_KEY in env or backend/.env")
        return 1

    emit("Building synthetic memory documents...")
    docs: dict[str, dict[str, Any]] = {
        "A": build_user_a_doc(),
        "B": build_user_b_doc(),
        "C": asyncio.run(build_user_c_doc()),
        "D": build_user_d_doc(),
        "E": build_user_e_doc(),
    }

    emit("Formatting memory blocks via _format_memory_block()...")
    memory_blocks: dict[str, str] = {k: _format_memory_block(v) for k, v in docs.items()}

    for user, block in memory_blocks.items():
        if not block:
            log.warning("empty_memory_block", user=user)
        else:
            emit(f"  User {user}: {len(block)} chars")

    emit("")
    emit(f"Running {len(QUESTIONS)} questions against {HAIKU_MODEL}...")
    client = Anthropic(api_key=api_key)
    results = run_benchmark(client, memory_blocks, QUESTIONS)

    summary = summarize(results)

    out_doc = {
        "model": HAIKU_MODEL,
        "memory_blocks": {k: v for k, v in memory_blocks.items()},
        "memory_docs": docs,
        "results": [
            {
                "qid": r.qid, "user": r.user, "category": r.category,
                "question": r.question, "ground_truth": r.ground_truth,
                "model_answer": r.model_answer, "score": r.score,
                "input_tokens": r.input_tokens, "output_tokens": r.output_tokens,
                "latency_ms": r.latency_ms,
            }
            for r in results
        ],
        "summary": summary,
    }
    results_file = RESULTS_DIR / f"{date.today().isoformat()}.json"
    results_file.write_text(json.dumps(out_doc, indent=2, default=str), encoding="utf-8")
    emit("")
    emit(f"Wrote results JSON to: {results_file}")

    write_report(memory_blocks, results, summary)
    return 0


if __name__ == "__main__":
    sys.exit(main())
