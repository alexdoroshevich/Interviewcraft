"""Expand question bank: more coding, system design, and company-specific questions.

Sources: industry-standard algorithmic problem concepts (not copyrighted),
system-design-primer (MIT license by Alex Xu), and well-known FAANG interview patterns.

Revision ID: 010
Revises: 009
Create Date: 2026-03-29
"""

from __future__ import annotations

import json
import uuid

import sqlalchemy as sa

from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── Coding questions (algorithmic concepts — not platform-specific phrasing) ──
    coding_questions = [
        # Arrays & Hashing
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given an integer array and a target integer, return the indices of the two numbers that add up to the target. Each input has exactly one solution and you cannot use the same element twice. What is the optimal time complexity you can achieve?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given an unsorted array of integers, find the length of the longest consecutive elements sequence. Can you solve it in O(n) time?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given a string, find the length of the longest substring without repeating characters. Walk me through your sliding window approach.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given an array of integers, find all unique triplets that sum to zero. How do you avoid duplicate triplets efficiently?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given an array of integers, find the contiguous subarray with the largest sum. Explain Kadane's algorithm and its time complexity.",
            "skills_tested": ["execution"],
        },
        # Two Pointers
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given a sorted array, remove duplicates in-place and return the new length. You may not use extra space. How do you approach this with two pointers?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given an elevation map where each bar has width 1, compute how much water can be trapped after raining. Walk me through the two-pointer approach versus the prefix sums approach.",
            "skills_tested": ["execution"],
        },
        # Stack & Queue
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given a string of brackets — parentheses, square brackets, and curly braces — determine if it is valid. All opened brackets must be closed in the correct order.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Design a Min Stack that supports push, pop, top, and retrieving the minimum element in constant time. What data structure do you use and why?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given a stream of integers, design a data structure that returns the median after each insertion in O(log n) time. Which data structures would you combine?",
            "skills_tested": ["execution"],
        },
        # Binary Search
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given a sorted rotated array where all values are unique, search for a target value and return its index, or -1 if not found. How does binary search work when the array is rotated?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given two sorted arrays of size m and n, find the median of the combined sorted array in O(log(m+n)) time. Walk me through the binary search on partition approach.",
            "skills_tested": ["execution"],
        },
        # Trees
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Invert a binary tree — swap left and right children at every node. What is the time and space complexity of your recursive versus iterative approach?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given a binary tree, perform level-order traversal and return all nodes grouped by level. Which traversal technique do you use and why?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Design a data structure to serialize and deserialize a binary tree. Your algorithm must produce a string from a tree and reconstruct the exact same tree from that string.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given the root of a binary tree, return the lowest common ancestor of two given nodes. How does your solution handle nodes that are ancestors of each other?",
            "skills_tested": ["execution"],
        },
        # Graphs
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given a 2D grid of '1's (land) and '0's (water), count the number of islands. Walk me through your BFS or DFS approach and discuss time complexity.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given a list of courses and their prerequisites, determine if it is possible to finish all courses. This is essentially cycle detection — which algorithm do you use?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given a directed graph, return a valid topological ordering of all nodes, or detect if a cycle exists. Compare Kahn's BFS algorithm with DFS-based topological sort.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "Given a list of words in a sorted alien language dictionary, derive the order of characters in that language. What graph algorithm determines the character ordering?",
            "skills_tested": ["execution"],
        },
        # Dynamic Programming
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given an amount and a list of coin denominations with unlimited supply, find the minimum number of coins needed to make up that amount. Walk me through the DP recurrence.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given two strings, find the length of their longest common subsequence. Explain how you build the DP table and derive the answer from it.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given a set of items each with a weight and value, and a knapsack with a weight capacity, find the maximum value you can carry. Explain the 0/1 knapsack DP approach.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "Given a string and a dictionary of words, determine if the string can be segmented into a sequence of dictionary words. How does memoization reduce repeated subproblem computation?",
            "skills_tested": ["execution"],
        },
        # Linked Lists
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l4",
            "text": "Given a linked list, reverse it in-place. Walk me through both the iterative approach with three pointers and the recursive approach, and compare their space complexity.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Design an LRU Cache that supports get and put operations in O(1) time. Which data structures do you combine and how do you maintain the access order?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Given two sorted linked lists, merge them into one sorted list. Can you do this without creating new nodes? What is the time and space complexity?",
            "skills_tested": ["execution"],
        },
        # Tries
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l5",
            "text": "Design and implement a Trie (prefix tree) with insert, search, and startsWith operations. When would you choose a Trie over a hash map for string storage?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "coding_discussion",
            "difficulty": "l6",
            "text": "Given a list of words, design a data structure that supports adding words and finding if any previously added string matches a search string where '.' can match any letter.",
            "skills_tested": ["execution"],
        },
    ]

    # ── Additional system design questions ────────────────────────────────────────
    sysdesign_questions = [
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a URL shortener service like bit.ly. Cover requirements clarification, capacity estimation, API design, database schema, short code generation, and caching for fast redirects.",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a distributed rate limiter that enforces per-user API call limits across a cluster of servers. Compare token bucket vs leaky bucket algorithms and discuss where state lives.",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a notification delivery system that can send push notifications, emails, and SMS at scale. How do you handle retries, delivery guarantees, and priority queuing?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a type-ahead search autocomplete system. How do you build the suggestion index, rank results by relevance, and serve suggestions with p99 < 100ms?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l6",
            "text": "Design a distributed message queue similar to Apache Kafka. Cover producer/consumer APIs, partition strategy, replication for durability, and consumer group offset management.",
            "skills_tested": ["execution", "technical_leadership"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a web crawler that can index one billion pages. How do you manage the crawl frontier, deduplicate URLs, respect robots.txt, and scale horizontally?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a proximity service like Yelp or Google Maps 'find restaurants near me'. How do you index and query geospatial data efficiently at scale?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l6",
            "text": "Design a live sports scoreboard that updates millions of users simultaneously with match scores in real time. Compare WebSockets, SSE, and long-polling for this use case.",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design a distributed job scheduler (like Google Cloud Scheduler or AWS EventBridge). How do you guarantee at-least-once execution, prevent duplicate runs, and handle failures?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": None,
            "type": "system_design",
            "difficulty": "l6",
            "text": "Design a hotel or flight reservation system with inventory management. How do you prevent double-booking under high concurrency without sacrificing throughput?",
            "skills_tested": ["execution", "technical_leadership"],
        },
        # Additional company-specific system design
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "system_design",
            "difficulty": "l6",
            "text": "Design Google Maps' ETA estimation system. How do you model real-time traffic, historical patterns, and route alternatives to produce accurate arrival time predictions at scale?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "meta",
            "type": "system_design",
            "difficulty": "l6",
            "text": "Design Facebook's photo storage and serving infrastructure at multi-billion scale. How do you handle deduplication, CDN strategy, and serving the long tail of rarely-accessed photos cheaply?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Amazon's order fulfillment pipeline. How does an order flow from checkout to warehouse pick-pack-ship, and how do you guarantee consistency across inventory, payment, and logistics services?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "microsoft",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design OneDrive's file sync engine. How do you detect changes, resolve conflicts when two devices edit the same file simultaneously, and sync efficiently on slow networks?",
            "skills_tested": ["execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "apple",
            "type": "system_design",
            "difficulty": "l5",
            "text": "Design Apple's iCloud photo sync across all a user's devices. How do you handle versioning, conflict resolution, and bandwidth-efficient delta sync while maintaining end-to-end encryption?",
            "skills_tested": ["execution", "customer_focus"],
        },
    ]

    # ── Additional behavioral questions per company ───────────────────────────────
    behavioral_extra = [
        # Google
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Googleyness check: tell me about a time you went out of your way to help a colleague or team that was not part of your direct responsibilities. What drove you to do it?",
            "skills_tested": ["cross_team", "communication"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "google",
            "type": "behavioral",
            "difficulty": "l6",
            "text": "Describe a time you had to make a significant architectural decision that would affect multiple teams or products. How did you gain consensus and what was the outcome?",
            "skills_tested": ["technical_leadership", "cross_team", "communication"],
        },
        # Meta
        {
            "id": str(uuid.uuid4()),
            "company": "meta",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Meta values being bold and moving fast. Tell me about a time you made a decision that felt risky but turned out to be the right call. What gave you the conviction to proceed?",
            "skills_tested": ["execution", "technical_leadership"],
        },
        # Amazon
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Customer Obsession: tell me about a time you went significantly out of your way to improve the customer experience, even when it was not in your direct scope of work.",
            "skills_tested": ["customer_focus", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Think Big: describe a time you proposed or drove an initiative that was significantly larger in scope than what others initially imagined was possible. What was the outcome?",
            "skills_tested": ["technical_leadership", "innovation", "execution"],
        },
        {
            "id": str(uuid.uuid4()),
            "company": "amazon",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Frugality: tell me about a time you accomplished more with fewer resources. What did you cut, what did you keep, and what was the business impact?",
            "skills_tested": ["execution", "data_driven_decision"],
        },
        # Microsoft
        {
            "id": str(uuid.uuid4()),
            "company": "microsoft",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Growth mindset is central to Microsoft's culture. Tell me about a time you fundamentally changed how you approached a problem after receiving feedback or new information.",
            "skills_tested": ["failure_recovery", "mentoring"],
        },
        # Netflix
        {
            "id": str(uuid.uuid4()),
            "company": "netflix",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Netflix prizes independent judgment over process. Describe a time you made a consequential decision without seeking approval. How did you decide you had enough information to act?",
            "skills_tested": ["execution", "data_driven_decision", "technical_leadership"],
        },
        # Stripe
        {
            "id": str(uuid.uuid4()),
            "company": "stripe",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Stripe cares deeply about the quality of its work. Tell me about a time you pushed back on shipping something because you felt it was not ready. How did you make the case and what happened?",
            "skills_tested": ["technical_leadership", "execution", "customer_focus"],
        },
        # Uber
        {
            "id": str(uuid.uuid4()),
            "company": "uber",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to lead a post-incident review or debug a production issue affecting customers. How did you communicate status, coordinate the response, and prevent recurrence?",
            "skills_tested": ["execution", "communication", "technical_leadership"],
        },
        # Airbnb
        {
            "id": str(uuid.uuid4()),
            "company": "airbnb",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Airbnb builds belonging. Tell me about a time your work had to balance the needs of two different communities or stakeholders with conflicting interests. How did you navigate that?",
            "skills_tested": ["customer_focus", "cross_team", "communication"],
        },
        # LinkedIn
        {
            "id": str(uuid.uuid4()),
            "company": "linkedin",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a product or feature you shipped that improved opportunities for the professionals who used it. How did you define and measure that impact?",
            "skills_tested": ["customer_focus", "data_driven_decision", "execution"],
        },
        # Spotify
        {
            "id": str(uuid.uuid4()),
            "company": "spotify",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Spotify runs in autonomous squads. Tell me about a time you had to deliver a complex feature end-to-end without a dedicated project manager. How did you keep things on track?",
            "skills_tested": ["execution", "cross_team", "technical_leadership"],
        },
        # Nvidia
        {
            "id": str(uuid.uuid4()),
            "company": "nvidia",
            "type": "behavioral",
            "difficulty": "l5",
            "text": "Tell me about a time you had to work at the intersection of hardware and software constraints. How did you align the two sides to ship a product that performed well on both dimensions?",
            "skills_tested": ["cross_team", "technical_leadership", "communication"],
        },
    ]

    all_questions = coding_questions + sysdesign_questions + behavioral_extra

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
            for q in all_questions
        ],
    )


def downgrade() -> None:
    # Questions added in this migration are not individually tracked —
    # they are seeded data and can be managed via the DB directly if needed.
    pass
