"""Expand question bank: behavioral STAR questions, coding concepts, ML/DS questions.

Original questions inspired by open-source interview content
(tech-interview-handbook MIT, FAQGURU MIT, Kaggle HR Questions CC0).
All text is original — no verbatim copying.

Adds:
  - 50 behavioral questions (10x technical leadership, 10x execution/delivery,
    10x cross-team collaboration, 10x failure/recovery, 10x conflict resolution)
  - 30 coding discussion questions (complexity, data structures, algorithms)
  - 20 ML / data science questions

Revision ID: 013
Revises: 012
Create Date: 2026-03-29
"""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa

from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 50 Behavioral — STAR competencies ─────────────────────────────────────

    # 10 × Technical leadership
    tech_leadership = [
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you drove the adoption of a new technology or engineering practice across your team. What resistance did you encounter and how did you get buy-in?",
            "skills_tested": ["leadership_stories", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a situation where you had to make a consequential technical architecture decision without full information. How did you decide, and how did you communicate the uncertainty to stakeholders?",
            "skills_tested": ["leadership_stories", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Tell me about a time you set the technical direction for a multi-quarter initiative that involved engineers outside your direct team. How did you establish credibility and keep everyone aligned?",
            "skills_tested": ["leadership_stories", "ownership_signal", "quantifiable_results"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a project where you had to balance paying down significant technical debt while also delivering new features on a tight deadline. How did you prioritize and what were the trade-offs?",
            "skills_tested": ["leadership_stories", "star_structure", "quantifiable_results"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Tell me about a time you deprecate or sunset a system that many teams depended on. How did you plan the migration, communicate the timeline, and support the teams through the transition?",
            "skills_tested": ["leadership_stories", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you identified a systemic reliability problem — not just a one-off incident — and drove the engineering effort to fix it. What metrics did you use to define success?",
            "skills_tested": ["leadership_stories", "quantifiable_results", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to evaluate and select a third-party technology (framework, database, cloud service) for a production system. What criteria did you use and what was the outcome?",
            "skills_tested": ["leadership_stories", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Describe a time you had to push back on product or leadership about the feasibility of a feature or timeline. How did you make the technical case and what happened?",
            "skills_tested": ["leadership_stories", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you introduced coding standards, review processes, or tooling that improved the quality of your team's output. How did you measure the improvement?",
            "skills_tested": ["leadership_stories", "quantifiable_results", "mentoring_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Describe a time you had to recover a project that was significantly behind schedule or at risk of not shipping. What actions did you take and what did you learn?",
            "skills_tested": ["leadership_stories", "ownership_signal", "star_structure"],
        },
    ]

    # 10 × Execution & delivery
    execution = [
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you delivered a feature or project from start to finish on your own. How did you scope the work, manage your time, and ensure quality?",
            "skills_tested": ["star_structure", "ownership_signal", "quantifiable_results"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Describe a time you had to manage multiple competing priorities simultaneously. How did you decide what to work on first, and what did you deprioritize?",
            "skills_tested": ["star_structure", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you took ownership of a critical bug or production issue that was not your fault. What did you do, and why did you step up?",
            "skills_tested": ["ownership_signal", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had an aggressive deadline and had to make scope trade-offs. What did you cut, what did you keep, and how did the team react?",
            "skills_tested": ["star_structure", "quantifiable_results", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you improved the velocity or efficiency of your team's delivery process. What change did you make and how did you measure the improvement?",
            "skills_tested": ["quantifiable_results", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you shipped a project that had ambiguous or frequently changing requirements. How did you keep the team focused while staying adaptable?",
            "skills_tested": ["star_structure", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you received critical feedback during a code review or design review that changed the direction of your work. How did you respond?",
            "skills_tested": ["star_structure", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you went above and beyond to ensure a launch was successful — beyond just writing code. What did you do and what was the impact?",
            "skills_tested": ["ownership_signal", "quantifiable_results", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to make a build-vs-buy decision for a key component of your system. How did you evaluate the options and what drove your conclusion?",
            "skills_tested": ["star_structure", "leadership_stories"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Describe a project where you proactively identified and mitigated a risk before it became a problem. How did you spot it and what actions did you take?",
            "skills_tested": ["ownership_signal", "star_structure"],
        },
    ]

    # 10 × Cross-team collaboration
    cross_team = [
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you worked closely with a non-engineering stakeholder (PM, designer, data scientist, or legal). What challenges came up and how did you navigate them?",
            "skills_tested": ["conflict_resolution", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had to coordinate a release or migration that required sign-off from multiple teams. How did you align everyone and handle blockers?",
            "skills_tested": ["ownership_signal", "star_structure", "conflict_resolution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you had to explain a complex technical concept to a non-technical audience. How did you tailor your communication?",
            "skills_tested": ["star_structure", "mentoring_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you partnered with another engineering team to build a shared platform or API. How did you decide on ownership, interface design, and SLA expectations?",
            "skills_tested": ["leadership_stories", "star_structure", "conflict_resolution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time a dependency on another team put your project at risk. How did you manage that relationship and what was the outcome?",
            "skills_tested": ["ownership_signal", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Describe a time you helped onboard a new team member or brought someone up to speed on a complex codebase. What did you do and what was the result?",
            "skills_tested": ["mentoring_signal", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you advocated for a change that benefited another team more than your own. What motivated you and what was the outcome?",
            "skills_tested": ["ownership_signal", "leadership_stories"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Describe a time you facilitated a difficult technical discussion between teams with opposing views. How did you create a shared understanding and move toward a decision?",
            "skills_tested": ["conflict_resolution", "leadership_stories"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you proactively shared knowledge or documentation that helped people outside your team do their work better.",
            "skills_tested": ["mentoring_signal", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had to align two teams that had different technical standards or approaches. How did you find common ground and what trade-offs did you accept?",
            "skills_tested": ["conflict_resolution", "leadership_stories", "star_structure"],
        },
    ]

    # 10 × Failure & recovery
    failure_recovery = [
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you made a mistake that had a real impact on your team or product. What happened, how did you handle it, and what did you change afterward?",
            "skills_tested": ["star_structure", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a production incident you were involved in — either as the person who caused it, responded to it, or led the post-mortem. What did you learn?",
            "skills_tested": ["star_structure", "ownership_signal", "quantifiable_results"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a project that did not go as planned. What went wrong, and looking back, what would you do differently?",
            "skills_tested": ["star_structure", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time your technical estimate turned out to be significantly off. What caused the gap, and how did you communicate and adapt?",
            "skills_tested": ["star_structure", "ownership_signal", "leadership_stories"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you received feedback that was hard to hear but ultimately made you a better engineer. How did you process and act on it?",
            "skills_tested": ["ownership_signal", "mentoring_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had to change course mid-project because your initial approach was flawed. How did you recognize the problem and pivot?",
            "skills_tested": ["star_structure", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you failed to meet a commitment you made to your team or a stakeholder. How did you handle the situation and rebuild trust?",
            "skills_tested": ["ownership_signal", "star_structure", "conflict_resolution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Describe a time you had to abandon work you had put significant effort into. How did you decide to stop, and how did you deal with it personally?",
            "skills_tested": ["star_structure", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Tell me about a time a strategic technical bet you advocated for did not pan out. How did you communicate the outcome and what did the team do next?",
            "skills_tested": ["leadership_stories", "ownership_signal", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had to deliver bad news — a slipped deadline, a dropped feature, or a failed experiment — to leadership or customers. How did you frame it and what happened?",
            "skills_tested": ["ownership_signal", "star_structure", "leadership_stories"],
        },
    ]

    # 10 × Conflict resolution
    conflict = [
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you disagreed with a technical decision your team or tech lead made. How did you raise your concern and what was the outcome?",
            "skills_tested": ["conflict_resolution", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had a significant disagreement with a peer engineer about how to implement something. How did you resolve it and what did you learn about working with that person?",
            "skills_tested": ["conflict_resolution", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to work with someone whose working style was very different from yours. What adjustments did you make and what was the result?",
            "skills_tested": ["conflict_resolution", "mentoring_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time you had to give critical feedback to a peer or direct report. How did you deliver it, and how did they respond?",
            "skills_tested": ["mentoring_signal", "conflict_resolution", "leadership_stories"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Tell me about a time you were in a code review where you and the author had a genuine disagreement about the right approach. How did you come to a resolution?",
            "skills_tested": ["conflict_resolution", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Describe a time you had to manage a conflict between two engineers on your team who were not getting along. What steps did you take and what was the outcome?",
            "skills_tested": ["leadership_stories", "conflict_resolution", "mentoring_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time engineering and product had fundamentally different views on what to build. How did you help bridge that gap?",
            "skills_tested": ["conflict_resolution", "leadership_stories"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l4",
            "text": "Describe a time you disagreed with your manager's decision. How did you handle it — did you escalate, comply, or find another path?",
            "skills_tested": ["conflict_resolution", "ownership_signal"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to build consensus around a technically controversial decision. What did you do to surface all perspectives and move to a conclusion?",
            "skills_tested": ["conflict_resolution", "leadership_stories", "star_structure"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Describe a time a stakeholder kept changing requirements mid-project and it was impacting delivery. How did you set boundaries and keep the team productive?",
            "skills_tested": ["conflict_resolution", "ownership_signal", "star_structure"],
        },
    ]

    # ── 30 Coding discussion questions ─────────────────────────────────────────

    coding = [
        # Complexity & trade-offs
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Explain the difference between O(n log n) and O(n²) sorting algorithms. When would you accept O(n²) over a faster alternative, and why?",
            "skills_tested": ["complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "When should you use a hash map versus a sorted array for a lookup problem? What are the time and space trade-offs, and when does constant factor matter more than asymptotic complexity?",
            "skills_tested": ["complexity_analysis", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain amortized analysis. Give an example where the worst case for a single operation is O(n) but the amortized cost across n operations is O(1). Why does this distinction matter in practice?",
            "skills_tested": ["complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "When is a greedy algorithm guaranteed to produce an optimal result versus just a good heuristic? Give an example of each and explain how you would prove or disprove correctness.",
            "skills_tested": ["complexity_analysis", "testing_approach"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain the trade-offs between memoization (top-down DP) and tabulation (bottom-up DP). When do you prefer each, and how does cache locality affect performance?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        # Data structure selection
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Compare a stack and a queue from an interface and use-case perspective. Give a real-world scenario where choosing the wrong one would produce incorrect results.",
            "skills_tested": ["code_review_reasoning", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "When would you choose a linked list over an array in a real production system? Consider insertion cost, cache performance, and memory allocation.",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain when a B-tree is preferred over a binary search tree in practice. Why do databases use B-trees internally, and what problem does that solve?",
            "skills_tested": ["code_review_reasoning", "complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain how a bloom filter works. What false positive and false negative guarantees does it provide, and give a concrete use case where this trade-off is acceptable.",
            "skills_tested": ["code_review_reasoning", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe the difference between a priority queue backed by a binary heap versus a Fibonacci heap. When does the theoretical advantage of the Fibonacci heap translate into a practical one?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        # Correctness & testing
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "What edge cases do you always check when writing an algorithm on arrays or strings? Walk me through your mental checklist before submitting code in an interview.",
            "skills_tested": ["edge_cases", "testing_approach"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "How do you test a function that depends on random behavior — for example, a shuffle or sampling function? What properties can you verify without fixing the random seed?",
            "skills_tested": ["testing_approach", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe your approach to testing a recursive algorithm. How do you verify the base case, the inductive step, and handle stack overflow risks?",
            "skills_tested": ["testing_approach", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "When writing unit tests for a data structure you implement from scratch, what invariants do you assert after every mutating operation? Give an example with a balanced BST.",
            "skills_tested": ["testing_approach", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "How would you prove that your implementation of Dijkstra's algorithm is correct? What invariant holds at the end of each iteration, and how do you test it?",
            "skills_tested": ["testing_approach", "complexity_analysis"],
        },
        # Code review & design
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "What are the most important things you look for when reviewing someone else's code? How do you balance correctness, performance, readability, and future maintainability?",
            "skills_tested": ["code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "When should you refactor a working but messy function versus leaving it as-is? What signals tell you that the complexity has crossed the threshold where refactoring pays off?",
            "skills_tested": ["code_review_reasoning", "complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain the single responsibility principle in the context of a function. How small should a function be, and how do you avoid creating many tiny functions that are hard to follow?",
            "skills_tested": ["code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe a time you came across code with a subtle concurrency bug during a code review. What patterns make concurrent code error-prone, and what review techniques help catch these?",
            "skills_tested": ["code_review_reasoning", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "How do you design a public API that is easy to use correctly and hard to use incorrectly? Give examples of good and bad API design patterns from libraries you have used.",
            "skills_tested": ["code_review_reasoning", "complexity_analysis"],
        },
        # Advanced topics
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain how consistent hashing works and why it is preferred over modulo-based hashing for distributing load across a dynamic set of servers.",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "What is the difference between optimistic and pessimistic locking? In which scenarios does optimistic locking outperform pessimistic locking, and when does it break down?",
            "skills_tested": ["code_review_reasoning", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "Explain the ABA problem in lock-free programming. Why does it occur with compare-and-swap, and what are the common mitigation strategies?",
            "skills_tested": ["complexity_analysis", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe the difference between parallelism and concurrency. Give a concrete example of each and explain when one is preferable over the other.",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Explain memory layout of arrays versus linked lists. How does cache locality affect performance, and when is the theoretical O-notation misleading in practice?",
            "skills_tested": ["complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe how garbage collection works in a language you have used professionally. What are the trade-offs between stop-the-world, incremental, and generational GC strategies?",
            "skills_tested": ["code_review_reasoning", "complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Walk me through how you would implement a thread-safe bounded queue (producer-consumer) without using high-level library primitives. What synchronization primitives do you use and why?",
            "skills_tested": ["complexity_analysis", "edge_cases", "testing_approach"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Explain tail call optimization. Which programming paradigms rely on it for correctness (not just performance), and how does it change how you write recursive algorithms?",
            "skills_tested": ["complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe how you would design a rate limiter at the code level (not system level). What data structure backs it, how do you handle time window boundaries, and what are the edge cases?",
            "skills_tested": ["edge_cases", "complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "Explain the trade-offs between row-oriented and column-oriented storage formats for analytical queries. Why do data warehouses use columnar formats and what makes them fast for aggregations?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
    ]

    # ── 20 ML / Data Science questions ────────────────────────────────────────

    ml_ds = [
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain the bias-variance trade-off. Give a concrete example of a model that is high-bias and one that is high-variance. How does regularization address the variance side?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "What is the difference between precision and recall? In a medical diagnosis model where false negatives are very costly, which metric should you optimize, and why?",
            "skills_tested": ["code_review_reasoning", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Explain cross-validation. Why is k-fold cross-validation preferable to a single train-test split when your dataset is small, and what is its computational cost?",
            "skills_tested": ["testing_approach", "complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe how gradient boosting differs from bagging (e.g., Random Forest). What does each ensemble method reduce — bias, variance, or both — and when would you choose one over the other?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain what data leakage is and give two real-world examples. Why is leakage particularly dangerous in time-series models, and how do you design your validation set to avoid it?",
            "skills_tested": ["edge_cases", "testing_approach"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Walk me through how you would handle class imbalance in a binary classification problem. What are the trade-offs between oversampling, undersampling, and modifying the loss function?",
            "skills_tested": ["code_review_reasoning", "complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain how attention mechanisms in transformer models differ from RNNs. What problem does the self-attention layer solve that recurrence cannot, and what are its computational costs?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe your approach to feature engineering for a tabular dataset with a mix of numerical, categorical, and high-cardinality string features. What transformations do you apply and why?",
            "skills_tested": ["code_review_reasoning", "testing_approach"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "How would you design an online learning system that updates a model in production as new data arrives? What are the risks of continuous retraining and how do you mitigate model drift?",
            "skills_tested": ["complexity_analysis", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain the vanishing and exploding gradient problems in deep neural networks. What architectural choices (batch norm, residual connections) and initialization strategies address them?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Describe the difference between L1 and L2 regularization. Why does L1 tend to produce sparse models and L2 tends to produce small but non-zero weights? When would you use each?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain how you would evaluate a recommendation system. What offline metrics can you measure without an A/B test, and what do they fail to capture about real user value?",
            "skills_tested": ["testing_approach", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Describe the embedding space in a neural collaborative filtering model for recommendations. How do you ensure embeddings for similar users or items end up close together?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "What is the curse of dimensionality? Give a concrete example where adding more features hurts model performance, and describe two techniques that address high dimensionality.",
            "skills_tested": ["complexity_analysis", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain the difference between correlation and causation in the context of data analysis. Describe how you would design an experiment to establish causality when a controlled trial is not feasible.",
            "skills_tested": ["testing_approach", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "How would you detect and handle outliers in a numeric feature before training a regression model? What impact do outliers have on different regression algorithms?",
            "skills_tested": ["edge_cases", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "Describe the challenges of serving a large language model in production at low latency. What techniques (quantization, distillation, caching) reduce inference cost and what is the accuracy trade-off?",
            "skills_tested": ["complexity_analysis", "code_review_reasoning"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Explain what A/B testing is and describe a scenario where a naive A/B test would give misleading results. How do novelty effects, network effects, and Twyman's Law affect your analysis?",
            "skills_tested": ["testing_approach", "edge_cases"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "How would you build a pipeline to automatically detect data quality issues (nulls, schema drift, distribution shift) before a daily ML training job runs?",
            "skills_tested": ["testing_approach", "edge_cases", "complexity_analysis"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "Explain the concept of model fairness. How would you measure whether a binary classifier treats demographic groups equitably, and what are the mathematical tensions between different fairness definitions?",
            "skills_tested": ["testing_approach", "edge_cases", "code_review_reasoning"],
        },
    ]

    all_questions = (
        tech_leadership + execution + cross_team + failure_recovery + conflict + coding + ml_ds
    )

    conn.execute(
        sa.text("""
            INSERT INTO questions (id, text, type, difficulty, skills_tested, company, status, times_used, created_at)
            VALUES (:id, :text, :type, :difficulty, CAST(:skills_tested AS jsonb), :company, 'approved', 0, now())
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
            for q in all_questions
        ],
    )


def downgrade() -> None:
    # Seeded questions are not individually tracked — manage via DB directly.
    pass
