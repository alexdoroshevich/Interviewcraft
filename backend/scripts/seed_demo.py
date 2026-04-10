#!/usr/bin/env python3
"""Seed a demo user with 10 realistic sessions + metrics.

Usage:
    python scripts/seed_demo.py

Requires DATABASE_URL in environment (or .env file in backend/).
Creates:
  - demo@interviewcraft.dev  /  demo1234
  - 10 sessions: 4 behavioral, 3 system design, 2 coding, 1 negotiation
  - ~30 segment scores with realistic score distributions
  - Skill graph nodes (22 microskills)
  - 5 stories covering 6 competencies
  - session_metrics rows (simulated latency)
  - usage_logs rows (simulated cost)

Safe to re-run — deletes and recreates the demo user each time.
"""

import asyncio
import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Resolve backend package whether running from repo root or inside backend/
_here = Path(__file__).resolve().parent
_backend_root = _here.parent if _here.name == "scripts" else _here
sys.path.insert(0, str(_backend_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(_backend_root / ".env")

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy import delete, select

from app.models.base import Base
from app.models.user import User, UserRole
from app.models.interview_session import InterviewSession
from app.models.segment_score import SegmentScore
from app.models.skill_graph_node import SkillGraphNode
from app.models.story import Story
from app.models.session_metrics import SessionMetrics
from app.models.usage_log import UsageLog
from app.services.auth.password import hash_password

DATABASE_URL = os.environ["DATABASE_URL"].replace("postgresql://", "postgresql+asyncpg://").replace("postgresql+psycopg2://", "postgresql+asyncpg://")

DEMO_EMAIL = "demo@interviewcraft.dev"
DEMO_PASSWORD = "demo1234"

random.seed(42)


def _dt(days_ago: float, hour: int = 10) -> datetime:
    return datetime.now(tz=timezone.utc) - timedelta(days=days_ago, hours=-hour)


def _dt_future(days_ahead: int) -> datetime:
    return datetime.now(tz=timezone.utc) + timedelta(days=days_ahead)


_TRANSCRIPT_TURNS: dict[str, list[dict]] = {
    "behavioral": [
        {"role": "assistant", "content": "Tell me about a time you had to influence without authority.", "ts_ms": 0},
        {"role": "user", "content": "At my previous company, I needed buy-in from three teams to adopt a new API contract. I documented pain points, proposed a design addressing all of them, ran a working group, and got unanimous agreement within two weeks.", "ts_ms": 3500},
    ],
    "system_design": [
        {"role": "assistant", "content": "Design a URL shortener that handles 100K requests per second.", "ts_ms": 0},
        {"role": "user", "content": "I would use Redis for hot URLs with base-62 short codes, sharded Postgres for persistence, and CDN edge caching for redirects so most requests never hit origin.", "ts_ms": 5000},
    ],
    "coding_discussion": [
        {"role": "assistant", "content": "Walk me through the time complexity and how you would test this solution.", "ts_ms": 0},
        {"role": "user", "content": "O(n log n) due to the sort, O(n) space. Tests: empty input, single element, all duplicates, already sorted, reverse sorted.", "ts_ms": 3000},
    ],
    "negotiation": [
        {"role": "assistant", "content": "The company has come back with 20K base and 0K equity over 4 years. How do you respond?", "ts_ms": 0},
        {"role": "user", "content": "I appreciate the offer. Based on my research and the scope of the role, I was expecting closer to 40K base. Is there flexibility there?", "ts_ms": 4500},
    ],
    "diagnostic": [
        {"role": "assistant", "content": "Tell me about a technical challenge you solved recently.", "ts_ms": 0},
        {"role": "user", "content": "I optimized a slow DB query causing page load timeouts. Added a composite index and fixed N+1 fetches, reducing p99 latency from 4s to 180ms.", "ts_ms": 4000},
    ],
}

_RULES: dict[str, list[dict]] = {
    "behavioral": [
        {"rule": "star_structure_complete", "confidence": "strong",
         "evidence": {"start_ms": 2000, "end_ms": 12000}, "score_delta": 8, "fix": None},
        {"rule": "result_not_quantified", "confidence": "medium",
         "evidence": {"start_ms": 8000, "end_ms": 11000}, "score_delta": -6,
         "fix": "Add a concrete metric such as reduced time by X% or saved Y per quarter"},
    ],
    "system_design": [
        {"rule": "scalability_addressed", "confidence": "strong",
         "evidence": {"start_ms": 3000, "end_ms": 8000}, "score_delta": 10, "fix": None},
        {"rule": "tradeoffs_not_discussed", "confidence": "medium",
         "evidence": {"start_ms": 5000, "end_ms": 9000}, "score_delta": -8,
         "fix": "Explicitly compare options: I chose X over Y because of Z"},
    ],
    "coding_discussion": [
        {"rule": "complexity_correct", "confidence": "strong",
         "evidence": {"start_ms": 1000, "end_ms": 4000}, "score_delta": 7, "fix": None},
    ],
    "negotiation": [
        {"rule": "anchor_above_target", "confidence": "strong",
         "evidence": {"start_ms": 2000, "end_ms": 6000}, "score_delta": 9, "fix": None},
    ],
    "diagnostic": [
        {"rule": "technical_depth_good", "confidence": "medium",
         "evidence": {"start_ms": 1000, "end_ms": 5000}, "score_delta": 6, "fix": None},
    ],
}

SESSIONS_SPEC = [
    {"type": "diagnostic",      "days_ago": 30, "scores": [62, 55]},
    {"type": "behavioral",      "days_ago": 27, "scores": [58, 63, 70]},
    {"type": "system_design",   "days_ago": 24, "scores": [51, 66]},
    {"type": "behavioral",      "days_ago": 21, "scores": [67, 71, 74]},
    {"type": "coding_discussion","days_ago": 18, "scores": [72, 65]},
    {"type": "system_design",   "days_ago": 14, "scores": [68, 79]},
    {"type": "behavioral",      "days_ago": 10, "scores": [74, 78, 82]},
    {"type": "coding_discussion","days_ago":  7, "scores": [77, 80]},
    {"type": "system_design",   "days_ago":  4, "scores": [82, 85]},
    {"type": "negotiation",     "days_ago":  1, "scores": []},
]

SKILL_NODES = [
    ("behavioral",       "star_structure",       72, "improving"),
    ("behavioral",       "situation_context",    68, "stable"),
    ("behavioral",       "task_ownership",       75, "improving"),
    ("behavioral",       "action_specificity",   64, "improving"),
    ("behavioral",       "result_quantification",61, "stable"),
    ("system_design",    "capacity_estimation",  70, "improving"),
    ("system_design",    "component_design",     65, "stable"),
    ("system_design",    "tradeoff_analysis",    58, "declining"),
    ("system_design",    "scalability_reasoning",63, "stable"),
    ("communication",    "conciseness",          74, "stable"),
    ("communication",    "structure_signposting",71, "improving"),
    ("communication",    "technical_vocabulary", 80, "stable"),
    ("coding_discussion","complexity_analysis",  77, "stable"),
    ("coding_discussion","testing_approach",     69, "improving"),
    ("coding_discussion","code_review_mindset",  72, "stable"),
    ("negotiation",      "anchoring",            55, "stable"),
    ("negotiation",      "value_articulation",   60, "stable"),
    ("negotiation",      "counter_strategy",     48, "declining"),
    ("negotiation",      "emotional_control",    63, "stable"),
]

STORIES = [
    {
        "title": "Led Database Migration at Scale",
        "summary": "Migrated 500GB Postgres to sharded Aurora without downtime",
        "competencies": ["technical_leadership", "execution"],
        "times_used": 2,
    },
    {
        "title": "Resolved Cross-Team API Conflict",
        "summary": "Mediated between Platform and Product on API contract, shipped in 2 weeks",
        "competencies": ["cross_team", "conflict_resolution"],
        "times_used": 1,
    },
    {
        "title": "Mentored Two Junior Engineers to Promotion",
        "summary": "Ran weekly 1:1s, pair programming, code review coaching over 6 months",
        "competencies": ["mentoring"],
        "times_used": 3,
    },
    {
        "title": "Recovered Failed Product Launch",
        "summary": "Identified root cause (cache invalidation), hotfix in 4 hours, 0 lost users",
        "competencies": ["failure_recovery", "execution"],
        "times_used": 1,
    },
    {
        "title": "Proposed and Shipped Search Rewrite",
        "summary": "Replaced Elasticsearch with pgvector, cut p99 latency 60%",
        "competencies": ["innovation", "data_driven_decision"],
        "times_used": 2,
    },
]


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Delete existing demo user (cascade handles child rows)
        existing = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        if user := existing.scalar_one_or_none():
            await db.delete(user)
            await db.commit()
            print(f"Deleted existing demo user {DEMO_EMAIL}")

        # Create demo user
        user = User()
        user.id = uuid.uuid4()
        user.email = DEMO_EMAIL
        user.hashed_password = hash_password(DEMO_PASSWORD)
        user.role = UserRole.user
        user.is_active = True
        db.add(user)
        await db.flush()
        print(f"Created demo user {DEMO_EMAIL}")

        # Create sessions + segments
        total_cost = 0.0
        for spec in SESSIONS_SPEC:
            sess = InterviewSession()
            sess.id = uuid.uuid4()
            sess.user_id = user.id
            sess.type = spec["type"]
            sess.status = "completed"
            sess.created_at = _dt(spec["days_ago"])
            sess.updated_at = _dt(spec["days_ago"])
            sess.transcript = _TRANSCRIPT_TURNS.get(spec["type"], [{"role": "assistant", "content": "Demo question.", "ts_ms": 0}, {"role": "user", "content": "Demo answer.", "ts_ms": 3000}])
            sess.lint_results = {}
            if spec["type"] == "negotiation":
                sess.lint_results = {
                    "negotiation_context": {
                        "company": "Acme Corp", "role": "Staff Engineer",
                        "level": "L6", "offer_amount": 220000,
                        "market_rate": 250000, "hidden_max": 253000,
                        "anchoring": 62, "value_articulation": 68,
                        "counter_strategy": 50, "emotional_control": 70,
                        "overall_score": 63, "money_left_on_table": 18000,
                    }
                }
            db.add(sess)

            for i, score in enumerate(spec["scores"]):
                seg = SegmentScore()
                seg.id = uuid.uuid4()
                seg.session_id = sess.id
                seg.segment_index = i
                seg.question_text = f"Demo question {i+1} for {spec['type']}"
                seg.answer_text = f"Demo answer demonstrating skill in {spec['type']}"
                seg.overall_score = score
                seg.confidence = "medium"
                seg.category_scores = {
                    "structure": score - random.randint(0, 8),
                    "depth": score + random.randint(0, 8),
                    "communication": score - random.randint(0, 5),
                    "seniority_signal": score + random.randint(0, 5),
                }
                rewind = random.choice([0, 0, 0, 1])
                seg.rewind_count = rewind
                seg.best_rewind_score = score + random.randint(8, 15) if rewind else None
                seg.rules_triggered = _RULES.get(spec["type"], [])[:1]
                seg.level_assessment = {
                    "l4_pass": score >= 50, "l5_pass": score >= 65,
                    "l5_borderline": 60 <= score < 65,
                    "l6_pass": score >= 80, "gaps": [],
                }
                seg.created_at = _dt(spec["days_ago"])
                db.add(seg)

            # session_metrics
            for _ in range(max(1, len(spec["scores"]) * 2)):
                m = SessionMetrics()
                m.id = uuid.uuid4()
                m.session_id = sess.id
                m.stt_latency_ms = random.randint(120, 280)
                m.llm_ttft_ms = random.randint(300, 650)
                m.tts_latency_ms = random.randint(80, 200)
                m.e2e_latency_ms = m.stt_latency_ms + m.llm_ttft_ms + m.tts_latency_ms + random.randint(20, 60)
                m.created_at = _dt(spec["days_ago"])
                db.add(m)

            # usage_logs
            session_cost = random.uniform(0.28, 0.65)
            total_cost += session_cost
            for op, provider, cost_frac in [
                ("voice_llm", "anthropic", 0.45),
                ("scoring_llm", "anthropic", 0.25),
                ("stt", "deepgram", 0.15),
                ("tts", "elevenlabs", 0.15),
            ]:
                ul = UsageLog()
                ul.id = uuid.uuid4()
                ul.session_id = sess.id
                ul.user_id = user.id
                ul.provider = provider
                ul.operation = op
                ul.cost_usd = round(session_cost * cost_frac, 6)
                ul.latency_ms = random.randint(200, 900)
                ul.cached = provider == "anthropic" and random.random() > 0.25
                ul.quality_profile = "balanced"
                ul.input_tokens = random.randint(800, 2000) if provider == "anthropic" else None
                ul.output_tokens = random.randint(200, 600) if provider == "anthropic" else None
                ul.cached_tokens = random.randint(500, 1000) if ul.cached else None
                ul.created_at = _dt(spec["days_ago"])
                db.add(ul)

        # Skill graph nodes
        for category, skill, score, trend in SKILL_NODES:
            node = SkillGraphNode()
            node.id = uuid.uuid4()
            node.user_id = user.id
            node.skill_name = skill
            node.skill_category = category
            node.current_score = score
            node.trend = trend
            node.evidence_links = []
            node.typical_mistakes = []
            node.best_score = score + random.randint(0, 10)
            node.next_review_due = _dt_future(random.randint(1, 7))
            node.created_at = _dt(28)
            node.updated_at = _dt(random.randint(1, 10))
            db.add(node)

        # Stories
        for story_data in STORIES:
            s = Story()
            s.id = uuid.uuid4()
            s.user_id = user.id
            s.title = story_data["title"]
            s.summary = story_data["summary"]
            s.competencies = story_data["competencies"]
            s.times_used = story_data["times_used"]
            s.warnings = ["OVERUSED: used 3+ times — prepare an alternative"] if story_data["times_used"] >= 3 else []
            s.auto_detected = False
            s.best_score_with_this_story = random.randint(68, 85)
            s.created_at = _dt(random.randint(10, 25))
            db.add(s)

        await db.commit()
        print(f"\nDemo seed complete!")
        print(f"  User:     {DEMO_EMAIL} / [see DEMO_PASSWORD constant]")
        print(f"  Sessions: {len(SESSIONS_SPEC)}")
        print(f"  Skills:   {len(SKILL_NODES)} nodes")
        print(f"  Stories:  {len(STORIES)}")
        print(f"  Est cost: ${total_cost:.3f}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
