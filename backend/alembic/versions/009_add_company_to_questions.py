"""Add company column to questions table and seed company-specific questions.

Revision ID: 009
Revises: 008
Create Date: 2026-03-28
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa

from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add company column ─────────────────────────────────────────────────
    op.add_column(
        "questions",
        sa.Column("company", sa.String(30), nullable=True),
    )
    op.create_index("ix_questions_company", "questions", ["company"])

    # ── 2. Seed company-specific questions ───────────────────────────────────
    conn = op.get_bind()

    questions = [
        # ── GOOGLE ─────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to work with a cross-functional team to solve a technically complex problem. How did you navigate conflicting priorities?",
            "skills_tested": ["cross_team", "communication", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a situation where you had to influence a decision without having direct authority. What was your approach and what was the outcome?",
            "skills_tested": ["cross_team", "communication", "technical_leadership"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Tell me about the most technically ambiguous project you have worked on. How did you scope it, make progress under uncertainty, and measure success?",
            "skills_tested": ["execution", "data_driven_decision", "innovation"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Google Search's crawl and indexing pipeline. Focus on how you would handle the scale of crawling billions of pages while keeping the index fresh.",
            "skills_tested": ["execution", "innovation"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a distributed key-value store like Google Bigtable. How would you handle consistency, partitioning, and failure recovery?",
            "skills_tested": ["execution"],
        },
        # ── META ────────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "meta",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you moved fast on a project despite significant uncertainty. What did you ship, what was the measurable result, and what would you do differently?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "meta",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had to make a data-driven product decision. What metrics did you use, how did you instrument the feature, and what did you learn from the data?",
            "skills_tested": ["data_driven_decision", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "meta",
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Tell me about a time you identified a significant opportunity or problem that others had missed. How did you build alignment and drive the initiative?",
            "skills_tested": ["technical_leadership", "cross_team", "innovation"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "meta",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design the Facebook News Feed ranking system. How would you decide what content to show each user, and how would you personalize it at 3 billion users?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "meta",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design WhatsApp's real-time messaging system. Focus on message delivery guarantees, end-to-end encryption at scale, and handling offline users.",
            "skills_tested": ["execution"],
        },
        # ── AMAZON ──────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you took ownership of a problem that was not strictly your responsibility. What did you do, and what was the result?",
            "skills_tested": ["execution", "technical_leadership"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a situation where you had to dive deep into data to understand a problem. What did you find and what action did you take as a result?",
            "skills_tested": ["data_driven_decision", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you disagreed with a decision made by your manager or team. How did you handle it, and what was the outcome?",
            "skills_tested": ["conflict_resolution", "communication"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Give me an example of a time you delivered results under a tight deadline or with limited resources. What tradeoffs did you make?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Amazon's product recommendation system. How would you build 'Customers who bought this also bought' at scale for hundreds of millions of products?",
            "skills_tested": ["execution"],
        },
        # ── MICROSOFT ───────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "microsoft",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to learn a completely new technology or domain under pressure. How did you approach it and what was the outcome?",
            "skills_tested": ["execution", "mentoring"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "microsoft",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a situation where you helped a teammate grow or overcome a challenge. What did you do and what was the impact on the team?",
            "skills_tested": ["mentoring", "cross_team", "communication"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "microsoft",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you received critical feedback and how you responded to it. What did you change as a result?",
            "skills_tested": ["failure_recovery", "communication"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "microsoft",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Microsoft Teams' video calling infrastructure. How would you handle real-time audio and video at scale, including network degradation and recording?",
            "skills_tested": ["execution"],
        },
        # ── APPLE ───────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "apple",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you pushed back on a feature or design decision because you felt it compromised quality or user experience. What was the outcome?",
            "skills_tested": ["technical_leadership", "customer_focus"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "apple",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a particularly difficult technical bug or performance problem you solved. Walk me through how you diagnosed and fixed it.",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "apple",
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Tell me about a project where you had to work within extremely tight constraints — time, memory, battery, or hardware. How did you make tradeoffs?",
            "skills_tested": ["execution", "customer_focus", "innovation"],
        },
        # ── NETFLIX ─────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "netflix",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a significant decision you made with incomplete information. How did you weigh the risks, and how did it turn out?",
            "skills_tested": ["data_driven_decision", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "netflix",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you chose to disagree and commit — you voiced your concerns, the team went another direction, and you fully executed on that direction. What happened?",
            "skills_tested": ["conflict_resolution", "execution", "communication"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "netflix",
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Tell me about a time you set the technical direction for a major initiative. How did you define the strategy, get buy-in, and drive execution across the team?",
            "skills_tested": ["technical_leadership", "cross_team", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "netflix",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Netflix's video streaming infrastructure. How would you handle adaptive bitrate streaming, CDN distribution, and ensuring sub-second playback start times globally?",
            "skills_tested": ["execution"],
        },
        # ── UBER ────────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "uber",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you shipped a high-stakes feature with reliability constraints. How did you balance speed of delivery with system stability?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "uber",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had to make a difficult tradeoff between technical debt and shipping speed. What did you decide and why?",
            "skills_tested": ["execution", "technical_leadership"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "uber",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Uber's surge pricing system. How do you calculate real-time supply and demand imbalances, compute surge multipliers, and communicate prices to riders within milliseconds?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "uber",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Uber's driver-rider matching algorithm. How do you assign the nearest available driver at scale across multiple cities simultaneously?",
            "skills_tested": ["execution"],
        },
        # ── STRIPE ──────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "stripe",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you prioritized correctness or reliability over shipping speed. How did you make that tradeoff and how did stakeholders react?",
            "skills_tested": ["execution", "technical_leadership"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "stripe",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you improved a developer experience or API design. What was wrong with the existing approach and what did you change?",
            "skills_tested": ["customer_focus", "innovation", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "stripe",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a payment processing system like Stripe's charge API. How do you ensure idempotency, handle partial failures, and audit every transaction?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "stripe",
            "type": "system_design",
            "difficulty": "l6",
            "text": "Design a distributed rate limiter for Stripe's API. How do you enforce per-customer rate limits across hundreds of API servers without a centralized bottleneck?",
            "skills_tested": ["execution", "technical_leadership"],
        },
        # ── LINKEDIN ────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "linkedin",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to balance user experience against monetization or business goals. How did you navigate the tension?",
            "skills_tested": ["customer_focus", "data_driven_decision", "cross_team"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "linkedin",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you used data or experimentation to challenge an assumption the team was making. What did you find and what changed?",
            "skills_tested": ["data_driven_decision", "communication"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "linkedin",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design LinkedIn's People You May Know feature. How do you compute second and third degree connections across a graph of 900 million members in real time?",
            "skills_tested": ["execution"],
        },
        # ── AIRBNB ──────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "airbnb",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to navigate a difficult tradeoff between business metrics and user or community trust. What did you decide?",
            "skills_tested": ["customer_focus", "data_driven_decision", "cross_team"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "airbnb",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time your work had a direct, positive impact on a user or community. How did you measure and validate that impact?",
            "skills_tested": ["customer_focus", "data_driven_decision", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "airbnb",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Airbnb's Smart Pricing system. How would you recommend nightly prices to hosts based on demand, seasonality, local events, and competitor pricing?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        # ── NVIDIA ──────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "nvidia",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a performance optimization you implemented. How did you profile the problem, identify the bottleneck, and measure the improvement?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "nvidia",
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Describe a time you had to bridge the gap between hardware constraints and software requirements. What tradeoffs did you make and how did you explain them to stakeholders?",
            "skills_tested": ["communication", "technical_leadership", "cross_team"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "nvidia",
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Walk me through how you would optimize a matrix multiplication operation for a GPU. What memory access patterns matter and how does CUDA handle thread hierarchy?",
            "skills_tested": ["execution"],
        },
        # ── SPOTIFY ─────────────────────────────────────────────────────────
        {
            "id": str(uuid.uuid4()),
            "company": "spotify",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you drove a project end-to-end in a self-organizing team. How did you align stakeholders without formal authority?",
            "skills_tested": ["technical_leadership", "cross_team", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "spotify",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a data-driven product decision you made that had a measurable impact on user engagement or creator success. What did the metrics tell you?",
            "skills_tested": ["data_driven_decision", "customer_focus", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "spotify",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Spotify's Discover Weekly recommendation system. How would you build a collaborative filtering model that generates personalized playlists for 400 million users every week?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
    ]

    import json

    conn.execute(
        sa.text("""
            INSERT INTO questions (id, text, type, difficulty, skills_tested, company, times_used, created_at)
            VALUES (:id, :text, :type, :difficulty, CAST(:skills_tested AS jsonb), :company, 0, now())
            ON CONFLICT (id) DO NOTHING
        """),
        [
            {
                "id": q["id"],
                "text": q["text"],
                "type": q["type"],
                "difficulty": q["difficulty"],
                "skills_tested": json.dumps(q["skills_tested"]),
                "company": q["company"],
            }
            for q in questions
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_questions_company", table_name="questions")
    op.drop_column("questions", "company")
