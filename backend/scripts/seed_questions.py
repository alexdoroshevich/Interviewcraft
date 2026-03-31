"""Seed the question bank with 205 SWE interview questions.

Run with:
    cd backend && python -m scripts.seed_questions

Requires DATABASE_URL in environment (from .env).
Each question has skills_tested[] mapped to the approved skill graph nodes:
  star_structure, quantifiable_results, tradeoff_analysis, capacity_estimation,
  conciseness, filler_word_control, ownership_signal, scalability_thinking,
  leadership_stories, mentoring_signal, anchoring, counter_strategy
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.question import Question

logger = structlog.get_logger(__name__)

# ── Question bank (205 questions) ─────────────────────────────────────────────
#
# Distribution:
#   behavioral:        60 questions (mix of l4/l5/l6)
#   system_design:     50 questions (mix of l4/l5/l6)
#   coding_discussion: 40 questions (mix of l4/l5/l6)
#   negotiation:       30 questions (all l5)
#   diagnostic:        25 questions (all l5)

QUESTIONS: list[dict] = [
    # ══════════════════════════════════════════════════════════════════════════
    # BEHAVIORAL — 60 questions
    # ══════════════════════════════════════════════════════════════════════════
    # -- behavioral / l4 (20) --
    {
        "text": "Tell me about a time you had to debug a critical production issue under pressure.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "quantifiable_results", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you had to deliver a project under a tight deadline with limited resources.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "ownership_signal", "quantifiable_results"],
    },
    {
        "text": "Describe a time when you had to learn a new technology quickly to solve a problem.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "quantifiable_results"],
    },
    {
        "text": "Describe a project where you collaborated closely with product and design. What were the challenges?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["leadership_stories", "conciseness"],
    },
    {
        "text": "Tell me about yourself, your background, what you are most proud of technically, and what you are looking for.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "conciseness", "filler_word_control"],
    },
    {
        "text": "Describe a recent project where you took ownership of a technical problem end-to-end.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["ownership_signal", "quantifiable_results", "star_structure"],
    },
    {
        "text": "Tell me about a bug that took you the longest to fix. What made it so difficult?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "ownership_signal", "tradeoff_analysis"],
    },
    {
        "text": "Describe a feature you built that you are particularly proud of. Why?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "quantifiable_results", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you received critical feedback on your code. How did you respond?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "conciseness", "ownership_signal"],
    },
    {
        "text": "Describe a situation where you had to work on an unfamiliar codebase. How did you ramp up?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you automated a manual process. What was the impact?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["quantifiable_results", "ownership_signal", "star_structure"],
    },
    {
        "text": "Describe a time you had to choose between two technical approaches with unclear tradeoffs.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "star_structure", "ownership_signal"],
    },
    {
        "text": "Tell me about a project where you underestimated the complexity. What happened?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "quantifiable_results", "ownership_signal"],
    },
    {
        "text": "Describe a time when you had to refactor legacy code. How did you approach it?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "star_structure", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you improved the performance of a slow system or feature.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["quantifiable_results", "star_structure", "tradeoff_analysis"],
    },
    {
        "text": "Describe a time you shipped a feature that did not go as expected. What did you learn?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "ownership_signal", "quantifiable_results"],
    },
    {
        "text": "Tell me about a time you had to balance quality with speed of delivery.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "star_structure", "conciseness"],
    },
    {
        "text": "Describe a situation where testing caught a significant bug before production. Walk me through it.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "ownership_signal", "quantifiable_results"],
    },
    {
        "text": "Tell me about a time you contributed to an open source project or shared knowledge broadly.",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "mentoring_signal", "ownership_signal"],
    },
    {
        "text": "Describe a situation where you had to onboard quickly to a new team. What was your approach?",
        "type": "behavioral",
        "difficulty": "l4",
        "skills_tested": ["star_structure", "conciseness", "ownership_signal"],
    },
    # -- behavioral / l5 (25) --
    {
        "text": "Describe a situation where you disagreed with your tech lead's technical decision. How did you handle it?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "ownership_signal", "star_structure"],
    },
    {
        "text": "Tell me about a time you mentored a junior engineer. What was your approach and the outcome?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["mentoring_signal", "leadership_stories", "quantifiable_results"],
    },
    {
        "text": "Describe the most complex technical project you have led. What was your role and what did you learn?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": [
            "star_structure",
            "leadership_stories",
            "quantifiable_results",
            "ownership_signal",
        ],
    },
    {
        "text": "Describe a time when you had to influence a cross-functional team without direct authority.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "ownership_signal", "conciseness"],
    },
    {
        "text": "Tell me about a significant technical failure you were responsible for. How did you handle it?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "star_structure", "quantifiable_results"],
    },
    {
        "text": "Tell me about a time you improved a team process or engineering practice.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "quantifiable_results", "mentoring_signal"],
    },
    {
        "text": "Describe a situation where you had to push back on a product requirement. How did you approach it?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "ownership_signal", "tradeoff_analysis"],
    },
    {
        "text": "Tell me about a time you had to make a technical decision with incomplete information.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "ownership_signal", "star_structure"],
    },
    {
        "text": "Tell me about your most impactful contribution at your current or last company.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["quantifiable_results", "ownership_signal", "star_structure"],
    },
    {
        "text": "Describe a time when you had to say no to a stakeholder request. How did you handle it?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "conciseness", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you identified a technical debt issue and drove its resolution.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "leadership_stories", "quantifiable_results"],
    },
    {
        "text": "Describe a time you led an architecture migration or major refactor across multiple services.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": [
            "leadership_stories",
            "tradeoff_analysis",
            "quantifiable_results",
            "ownership_signal",
        ],
    },
    {
        "text": "Tell me about a time you had to build consensus among engineers who had different strong opinions.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "conciseness", "ownership_signal"],
    },
    {
        "text": "Describe a situation where a teammate was underperforming. How did you handle it?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["mentoring_signal", "leadership_stories", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you introduced a new technology or tool to your team. How did you get buy-in?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "tradeoff_analysis", "quantifiable_results"],
    },
    {
        "text": "Describe a time you had to scope down a project mid-flight. What were the tradeoffs?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "star_structure", "conciseness", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you had to manage competing priorities from different stakeholders.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "ownership_signal", "conciseness"],
    },
    {
        "text": "Describe a major incident you helped resolve. What was your role in the post-mortem?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": [
            "ownership_signal",
            "star_structure",
            "quantifiable_results",
            "leadership_stories",
        ],
    },
    {
        "text": "Tell me about a time you onboarded multiple new engineers to a complex system. What was your strategy?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["mentoring_signal", "leadership_stories", "conciseness"],
    },
    {
        "text": "Describe a project where you had to coordinate across three or more teams. What made it successful or difficult?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "ownership_signal", "star_structure"],
    },
    {
        "text": "Tell me about a time you championed an unpopular technical decision that turned out well.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "leadership_stories", "quantifiable_results"],
    },
    {
        "text": "Describe a situation where you had to balance innovation with reliability for a critical system.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "ownership_signal", "star_structure"],
    },
    {
        "text": "Tell me about a time you set technical direction for a new project from scratch.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "tradeoff_analysis", "ownership_signal"],
    },
    {
        "text": "Describe a time you successfully transitioned a legacy monolith to microservices. What was the plan?",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": [
            "tradeoff_analysis",
            "scalability_thinking",
            "star_structure",
            "leadership_stories",
        ],
    },
    {
        "text": "Tell me about a time you had to deliver hard news to your manager about project delays.",
        "type": "behavioral",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "conciseness", "star_structure"],
    },
    # -- behavioral / l6 (15) --
    {
        "text": "Describe a time you defined the technical strategy for a product area spanning multiple teams.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "leadership_stories",
            "tradeoff_analysis",
            "ownership_signal",
            "scalability_thinking",
        ],
    },
    {
        "text": "Tell me about the most significant organizational change you drove as a technical leader.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": ["leadership_stories", "ownership_signal", "quantifiable_results"],
    },
    {
        "text": "Describe a time you had to sunset a critical system. How did you manage risk and stakeholders?",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "leadership_stories",
            "tradeoff_analysis",
            "ownership_signal",
            "star_structure",
        ],
    },
    {
        "text": "Tell me about a time you built an engineering culture of quality in a new or struggling team.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": ["mentoring_signal", "leadership_stories", "ownership_signal"],
    },
    {
        "text": "Describe a decision you made that affected the company's bottom line by more than a million dollars.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "quantifiable_results",
            "leadership_stories",
            "ownership_signal",
            "tradeoff_analysis",
        ],
    },
    {
        "text": "Tell me about a time you had to re-org or restructure your team to meet new business goals.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": ["leadership_stories", "ownership_signal", "mentoring_signal"],
    },
    {
        "text": "Describe a technical bet you made that failed. How did you recover and what did you learn?",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "ownership_signal",
            "star_structure",
            "quantifiable_results",
            "leadership_stories",
        ],
    },
    {
        "text": "Tell me about a time you drove a multi-quarter platform investment. How did you secure executive buy-in?",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "leadership_stories",
            "quantifiable_results",
            "tradeoff_analysis",
            "ownership_signal",
        ],
    },
    {
        "text": "Describe how you have established engineering standards or best practices adopted across your organization.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": ["leadership_stories", "mentoring_signal", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you resolved a deep cross-team technical dependency conflict.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": ["leadership_stories", "ownership_signal", "tradeoff_analysis"],
    },
    {
        "text": "Describe a situation where you identified a company-level risk through technical analysis and raised it.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": ["ownership_signal", "leadership_stories", "quantifiable_results"],
    },
    {
        "text": "Tell me about a time you had to shut down a project your team was passionate about. How did you handle morale?",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "leadership_stories",
            "mentoring_signal",
            "ownership_signal",
            "conciseness",
        ],
    },
    {
        "text": "Describe how you have mentored someone from junior to senior level. What was your approach over time?",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": ["mentoring_signal", "leadership_stories", "quantifiable_results"],
    },
    {
        "text": "Tell me about a time you led a company-wide reliability initiative. What changed?",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "leadership_stories",
            "quantifiable_results",
            "scalability_thinking",
            "ownership_signal",
        ],
    },
    {
        "text": "Describe a technology migration you led that spanned more than six months and multiple teams.",
        "type": "behavioral",
        "difficulty": "l6",
        "skills_tested": [
            "leadership_stories",
            "tradeoff_analysis",
            "ownership_signal",
            "quantifiable_results",
        ],
    },
    # ══════════════════════════════════════════════════════════════════════════
    # SYSTEM DESIGN — 50 questions
    # ══════════════════════════════════════════════════════════════════════════
    # -- system_design / l4 (15) --
    {
        "text": "Design a URL shortening service like bit.ly that handles 100 million URLs.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design Instagram's photo upload and feed generation system.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a simple key-value store that supports get, put, and delete operations.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a paste-bin service like Pastebin that stores text snippets with expiry.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis"],
    },
    {
        "text": "Design a task queue system that reliably processes background jobs.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a basic chat application for one-on-one messaging between users.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a leaderboard system for a mobile game with millions of players.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a file upload service that handles files up to 5GB in size.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Design a basic e-commerce product catalog with search functionality.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a logging aggregation service for a small microservices deployment.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis"],
    },
    {
        "text": "Design a URL bookmarking service with tagging, search, and sharing.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a poll / voting system that can handle spikes during live events.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["capacity_estimation", "scalability_thinking"],
    },
    {
        "text": "Design a basic notification service that sends push notifications to mobile devices.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a coupon / promo code system for an online store.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Design a simple ride-sharing price estimation service.",
        "type": "system_design",
        "difficulty": "l4",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis", "scalability_thinking"],
    },
    # -- system_design / l5 (25) --
    {
        "text": "Design Twitter's timeline feature. Users should see tweets from people they follow in near-real-time.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a real-time notification system for a social media platform with 50M DAU.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a distributed job scheduling system like cron at scale.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design Google Drive's file storage and sync system.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a search autocomplete system that handles 10 billion queries per day.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a video streaming platform like YouTube, focusing on the video ingestion and delivery pipeline.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design an API gateway for a microservices architecture with 100 services.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design a recommendation system for an e-commerce platform.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a payments processing system for a marketplace with buyers and sellers.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design a ride-sharing service like Uber, focusing on matching riders with drivers in real-time.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a web crawler that can index a billion pages per week.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a type-ahead search system for a large email client like Gmail.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design a collaborative document editor like Google Docs.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a metrics collection and alerting system for a cloud infrastructure provider.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a food delivery service like DoorDash, focusing on order routing and dispatch.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a social media news feed ranking system that balances relevance and recency.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design a distributed locking service for coordinating access to shared resources.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a hotel booking system like Booking.com, focusing on availability and pricing.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a geographically distributed database for a global SaaS application.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Design a feature flag system used by thousands of engineers across hundreds of services.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a ticket-selling system like Ticketmaster that handles flash sales without overselling.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a real-time multiplayer game backend that supports 100K concurrent matches.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a content moderation pipeline for user-generated content at scale.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Design a location-based service that finds nearby points of interest in real-time.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a CI/CD pipeline service that builds, tests, and deploys code for thousands of developers.",
        "type": "system_design",
        "difficulty": "l5",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    # -- system_design / l6 (10) --
    {
        "text": "Design a distributed rate limiter that works across multiple data centers.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design a distributed cache system like Redis from scratch.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design a pub/sub messaging system for a fintech company processing 1M transactions per minute.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Design a global content delivery network (CDN) from the ground up.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Design a distributed consensus system (like Raft or Paxos) for leader election at scale.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Design a multi-region active-active database replication system with conflict resolution.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Design a distributed tracing system like Jaeger or Zipkin for a 500-service architecture.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a global-scale identity and access management system with sub-100ms auth latency.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Design a streaming data processing pipeline like Apache Flink for real-time analytics.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Design a container orchestration system (like a simplified Kubernetes) for deploying and scaling services.",
        "type": "system_design",
        "difficulty": "l6",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    # ══════════════════════════════════════════════════════════════════════════
    # CODING DISCUSSION — 40 questions
    # ══════════════════════════════════════════════════════════════════════════
    # -- coding_discussion / l4 (15) --
    {
        "text": "Walk me through how you would approach optimizing a slow SQL query in production.",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "Explain the tradeoffs between SQL and NoSQL databases. When would you choose each?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Walk me through how you would conduct a code review for a complex PR.",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["mentoring_signal", "conciseness"],
    },
    {
        "text": "Explain the difference between a thread and a process. How do you handle concurrency in your language of choice?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "What is the time complexity of common operations in a hash map? When would it degrade?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "Explain how a garbage collector works. What are the tradeoffs of different GC strategies?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "When would you use a stack versus a queue? Give a real-world example for each.",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "Explain what happens when you type a URL into a browser and press Enter.",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["conciseness", "scalability_thinking"],
    },
    {
        "text": "What is a race condition? Give an example and explain how you would prevent it.",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "Explain the difference between an interface and an abstract class. When would you use each?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "How do you decide between recursion and iteration for a problem? What are the tradeoffs?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "Explain the SOLID principles. Which one do you think is most important and why?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "What are the different ways to handle errors in a web application? Compare exceptions, error codes, and result types.",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "Explain the concept of database indexing. When can indexes hurt performance?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "What is the difference between optimistic and pessimistic locking? When would you use each?",
        "type": "coding_discussion",
        "difficulty": "l4",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    # -- coding_discussion / l5 (18) --
    {
        "text": "How would you design a system to handle 10x traffic suddenly? Walk me through your thought process.",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "Explain CAP theorem and give a real example where you had to make a consistency vs availability tradeoff.",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "How do you think about testing strategy for a distributed microservices system?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "ownership_signal"],
    },
    {
        "text": "How would you debug a memory leak in a production service?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "ownership_signal"],
    },
    {
        "text": "What are your strategies for ensuring backward compatibility when making API changes?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "How do you approach system observability? What do you log, what metrics do you track, and how?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Describe your approach to incident response. How do you handle a P0 outage?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "star_structure", "conciseness"],
    },
    {
        "text": "Explain eventual consistency and how you would design around it in a user-facing product.",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Compare different approaches to database sharding. When would each be appropriate?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["scalability_thinking", "tradeoff_analysis", "capacity_estimation"],
    },
    {
        "text": "How would you design a zero-downtime deployment strategy for a stateful service?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Explain the differences between gRPC, REST, and GraphQL. How do you choose between them?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "What is the Saga pattern? When would you use it instead of distributed transactions?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "How do you approach capacity planning for a new service? Walk me through your methodology.",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "Explain how you would implement a circuit breaker pattern. What are the key parameters?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "How would you design a data pipeline that needs exactly-once processing semantics?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Explain the tradeoffs between synchronous and asynchronous communication in microservices.",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "How would you migrate a running system from one database to another with zero data loss?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "ownership_signal", "scalability_thinking"],
    },
    {
        "text": "Compare write-ahead logs, event sourcing, and CQRS. When is each the right choice?",
        "type": "coding_discussion",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    # -- coding_discussion / l6 (7) --
    {
        "text": "How would you design a system that provides linearizability across multiple data centers?",
        "type": "coding_discussion",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "Explain the tradeoffs of different consensus algorithms: Paxos, Raft, and PBFT.",
        "type": "coding_discussion",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "How would you design a garbage collector for a language runtime? Compare generational, concurrent, and region-based approaches.",
        "type": "coding_discussion",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "conciseness"],
    },
    {
        "text": "Discuss the tradeoffs in designing a distributed file system. Compare GFS, HDFS, and modern alternatives.",
        "type": "coding_discussion",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    {
        "text": "How do CRDTs work and when would you choose them over operational transformation?",
        "type": "coding_discussion",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "Explain the internals of a B-tree index. How does it compare to an LSM-tree for different workloads?",
        "type": "coding_discussion",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking"],
    },
    {
        "text": "How would you design a query optimizer for a distributed SQL database?",
        "type": "coding_discussion",
        "difficulty": "l6",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "capacity_estimation"],
    },
    # ══════════════════════════════════════════════════════════════════════════
    # NEGOTIATION — 30 questions (all l5)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "text": "We'd like to offer you a base salary of $180K. Does that work for you?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["anchoring", "counter_strategy"],
    },
    {
        "text": "We're at the top of our band for this role. The equity should more than make up the difference.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "Your current competing offer is higher, but we think our culture and impact are worth more. What do you think?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We can do $195K but that's our final offer. I need an answer by end of day.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We normally don't negotiate on base salary for this level. Is equity something you'd consider instead?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "What salary range are you expecting for this role?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["anchoring", "counter_strategy"],
    },
    {
        "text": "We've benchmarked this role at $170K. That's competitive for our market. How does that sound?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "I understand you want $200K, but our budget for this role maxes out at $185K. Can we find a middle ground?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We can offer a $15K signing bonus instead of a higher base. Would that work?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "Other candidates at your level accepted our initial offer. Why should we go higher for you?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["anchoring", "counter_strategy"],
    },
    {
        "text": "Your experience is impressive but you don't have direct experience in our domain. That affects the offer level.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We can revisit compensation after six months based on performance. Can you start at this level for now?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "The total compensation package including benefits is actually worth $250K. The base is just one part.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We really want you on the team. What would it take for you to accept today?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["anchoring", "counter_strategy"],
    },
    {
        "text": "I can try to get approval for $190K but I need to justify it to the comp team. Help me make the case.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["anchoring", "counter_strategy"],
    },
    {
        "text": "We offer four weeks of PTO and full remote flexibility. Does that change how you think about the base?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "Your ask is $20K above our range. I need to get VP approval for that. What if we split the difference?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We're a pre-IPO company. The equity upside could be worth multiples of that salary difference.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We'd love to bring you on as a senior engineer. The offer is $175K base with standard equity. Your thoughts?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["anchoring", "counter_strategy"],
    },
    {
        "text": "I see you're currently at $165K. We're offering a 15% increase. That's a strong bump.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "Honestly, we've never paid anyone at this level more than $190K. Your ask of $210K is outside our range.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We can't match the FAANG offer on cash, but our work-life balance and mission are unmatched.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "If we increase the base to $185K, can you commit to a two-year stay?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We're flexible on the start date and can offer relocation assistance. How does that factor in?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "The role is scoped at L5 for now, but we expect a quick promotion to L6 within 12 months.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "Your competing offer has a higher base but lower equity. Looking at four-year total comp, we're actually higher.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "We have a strict no-negotiation policy on base salary. Everyone at this level gets the same. But we can adjust the equity grant.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "I'll be honest — we've lost candidates to higher offers before. What's most important to you beyond salary?",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["anchoring", "counter_strategy"],
    },
    {
        "text": "We've extended the offer at $188K. I know you were hoping for $205K. Let's talk about how to close this gap.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    {
        "text": "Our board just approved a new equity refresh program. Staying two years could net you an additional 50% equity.",
        "type": "negotiation",
        "difficulty": "l5",
        "skills_tested": ["counter_strategy", "anchoring"],
    },
    # ══════════════════════════════════════════════════════════════════════════
    # DIAGNOSTIC — 25 questions (all l5, broad skill coverage)
    # ══════════════════════════════════════════════════════════════════════════
    {
        "text": "Walk me through a project you are most proud of. What was the problem, your approach, and the outcome?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["star_structure", "quantifiable_results", "ownership_signal"],
    },
    {
        "text": "If you had to design a system to handle millions of events per second, where would you start?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "How do you decide when to refactor code versus when to leave it alone?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "ownership_signal", "conciseness"],
    },
    {
        "text": "Describe your ideal engineering team culture. How have you contributed to building that in the past?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "mentoring_signal", "conciseness"],
    },
    {
        "text": "What is the hardest technical problem you have solved? Walk me through your approach step by step.",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["star_structure", "ownership_signal", "quantifiable_results"],
    },
    {
        "text": "How do you approach mentoring someone who is struggling with a concept?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["mentoring_signal", "leadership_stories", "conciseness"],
    },
    {
        "text": "If I gave you a system with 99th percentile latency of 5 seconds, how would you diagnose and fix it?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "ownership_signal"],
    },
    {
        "text": "Tell me about a time you had to make a tradeoff between two good options. How did you decide?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "star_structure", "conciseness"],
    },
    {
        "text": "How do you keep your technical skills current? Give me a recent example.",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "conciseness", "star_structure"],
    },
    {
        "text": "Estimate the storage requirements for a service that stores 10 million user profiles with photos.",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "conciseness"],
    },
    {
        "text": "How would you explain a complex technical concept to a non-technical stakeholder?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["conciseness", "filler_word_control", "leadership_stories"],
    },
    {
        "text": "What is the most impactful code review feedback you have ever given or received?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["mentoring_signal", "ownership_signal", "star_structure"],
    },
    {
        "text": "If you were starting a new service from scratch today, what would your tech stack be and why?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "scalability_thinking", "conciseness"],
    },
    {
        "text": "Describe how you would estimate the number of servers needed for a service with 10M daily active users.",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking"],
    },
    {
        "text": "What is your approach to writing clean, maintainable code? Give a concrete example.",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["conciseness", "ownership_signal", "star_structure"],
    },
    {
        "text": "How do you prioritize what to work on when everything seems urgent?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "ownership_signal", "conciseness"],
    },
    {
        "text": "Tell me about a time you had to communicate a technical risk to leadership. How did you frame it?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "conciseness", "filler_word_control"],
    },
    {
        "text": "What makes a good API? Describe an API you have designed that you are proud of.",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["tradeoff_analysis", "ownership_signal", "conciseness"],
    },
    {
        "text": "How do you handle disagreements about technical direction with a peer?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "conciseness", "ownership_signal"],
    },
    {
        "text": "If a junior engineer asked you how to grow into a senior role, what advice would you give?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["mentoring_signal", "leadership_stories", "conciseness"],
    },
    {
        "text": "Walk me through how you would size a database for a new product expecting rapid growth.",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["capacity_estimation", "scalability_thinking", "tradeoff_analysis"],
    },
    {
        "text": "What is the most important lesson you have learned about building software in production?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "conciseness", "star_structure"],
    },
    {
        "text": "How do you ensure your team delivers high-quality work without slowing down?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["leadership_stories", "tradeoff_analysis", "mentoring_signal"],
    },
    {
        "text": "Describe a time you used data to make a technical decision. What data did you look at?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["quantifiable_results", "star_structure", "tradeoff_analysis"],
    },
    {
        "text": "If you could go back and redo one technical decision in your career, what would it be and why?",
        "type": "diagnostic",
        "difficulty": "l5",
        "skills_tested": ["ownership_signal", "tradeoff_analysis", "star_structure"],
    },
]


# ── Runner ─────────────────────────────────────────────────────────────────────


async def seed(database_url: str) -> None:
    """Seed the question bank. Skips if >100 questions already exist."""
    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with session_factory() as db:
        # Check how many questions already exist
        count_result = await db.execute(select(func.count(Question.id)))
        existing_count = count_result.scalar() or 0

        if existing_count > 100:
            logger.info(
                "question_bank_already_seeded",
                existing_count=existing_count,
                msg="Skipping seed — more than 100 questions already exist.",
            )
            print(f"Skipping: {existing_count} questions already exist (threshold: >100).")
            await engine.dispose()
            return

        # Get existing question texts to avoid duplicates
        result = await db.execute(select(Question.text))
        existing_texts = {row[0] for row in result.all()}

        added = 0
        skipped = 0
        for q_data in QUESTIONS:
            if q_data["text"] in existing_texts:
                skipped += 1
                continue

            question = Question(
                text=q_data["text"],
                type=q_data["type"],
                difficulty=q_data["difficulty"],
                skills_tested=q_data["skills_tested"],
            )
            db.add(question)
            added += 1

        await db.commit()

        logger.info(
            "question_bank_seeded",
            added=added,
            skipped=skipped,
            total=existing_count + added,
        )
        print(f"Seed complete: {added} questions added, {skipped} duplicates skipped.")
        print(f"Total in bank: {existing_count + added}")

    await engine.dispose()


def _get_database_url() -> str:
    """Resolve database URL from app config or environment."""
    try:
        from app.config import settings

        return settings.database_url
    except Exception:
        return os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://interviewcraft:interviewcraft@localhost:5432/interviewcraft",
        )


if __name__ == "__main__":
    db_url = _get_database_url()
    asyncio.run(seed(db_url))
