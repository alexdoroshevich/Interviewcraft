"""Interview scoring rubric — 15 rules defined as data.

Rules are static and used as the Anthropic prompt-cached prefix.
The cached prefix saves ~90% on repeat scoring calls vs. re-sending
the full rubric every time.

Categories:
  structure         — STAR format, results, metrics
  depth             — tradeoffs, assumptions, follow-up depth
  communication     — length, filler words, ownership
  seniority_signal  — scale thinking, stakeholder management, mentoring
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Rule:
    """A single scoring rule.

    Attributes:
        id:          Machine-readable identifier used in LLM responses.
        name:        Human-readable short label.
        description: What the rule checks for and why it matters.
        category:    One of: structure | depth | communication | seniority_signal.
        applies_to:  Question types this rule applies to ("all" or specific types).
        weight:      Score-impact multiplier (default 1.0).
    """

    id: str
    name: str
    description: str
    category: str
    applies_to: list[str] = field(default_factory=lambda: ["all"])
    weight: float = 1.0


# ── The 15 rules ───────────────────────────────────────────────────────────────

RULES: list[Rule] = [
    # ── STRUCTURE ──────────────────────────────────────────────────────────────
    Rule(
        id="no_star_structure",
        name="No STAR Structure",
        description=(
            "Answer lacks Situation/Task/Action/Result framing. "
            "Without STAR, answers are hard to evaluate and appear unstructured. "
            "Fix: open with the situation in 1-2 sentences, state the task/challenge, "
            "describe YOUR specific actions, then state the measurable result."
        ),
        category="structure",
        applies_to=["behavioral", "all"],
        weight=1.2,
    ),
    Rule(
        id="missing_result",
        name="No Outcome Stated",
        description=(
            "Answer describes actions but never states what happened. "
            "Interviewers need to hear the outcome to assess impact. "
            "Fix: always close with 'The result was...' or 'This led to...' "
            "followed by a specific, measurable outcome."
        ),
        category="structure",
        applies_to=["all"],
        weight=1.2,
    ),
    Rule(
        id="result_not_specific",
        name="Vague Result",
        description=(
            "Result exists but is too vague to be credible: "
            "'improved performance', 'made it faster', 'the team was happy'. "
            "Fix: quantify — latency numbers, percentages, dollar impact, "
            "user counts, time saved. E.g. 'reduced p95 from 800ms to 120ms'."
        ),
        category="structure",
        applies_to=["all"],
        weight=1.1,
    ),
    Rule(
        id="missing_metrics",
        name="No Numbers",
        description=(
            "Answer contains zero quantifiable data points — no percentages, "
            "dollar amounts, latency figures, user counts, team sizes, or timelines. "
            "Fix: add at least 2 data points to anchor the story in reality. "
            "If exact numbers aren't remembered, use ranges: '$100K-200K savings'."
        ),
        category="structure",
        applies_to=["all"],
        weight=1.0,
    ),
    # ── DEPTH ──────────────────────────────────────────────────────────────────
    Rule(
        id="no_tradeoff",
        name="No Tradeoff Discussion",
        description=(
            "Answer presents a decision without discussing alternatives considered "
            "or why this option was chosen over others. Senior engineers always "
            "acknowledge tradeoffs. "
            "Fix: 'I chose X over Y because... The tradeoff was Z, which we accepted "
            "because...' This signals engineering maturity."
        ),
        category="depth",
        applies_to=["system_design", "behavioral", "coding_discussion"],
        weight=1.3,
    ),
    Rule(
        id="no_assumptions",
        name="No Stated Assumptions",
        description=(
            "System design answer dives into solutions without stating what is assumed "
            "about scale, data volume, consistency requirements, or SLAs. "
            "Fix: begin with 'Assuming X QPS, Y GB/day, Z users...' to show "
            "structured thinking and make the solution evaluable."
        ),
        category="depth",
        applies_to=["system_design"],
        weight=1.2,
    ),
    Rule(
        id="shallow_followup",
        name="Couldn't Go Deeper",
        description=(
            "When the interviewer probed further, the answer became vague, "
            "deflected, or repeated the same top-level summary. "
            "Fix: prepare 2-3 layers of depth for each story — what happened, "
            "why that approach, what you'd do differently."
        ),
        category="depth",
        applies_to=["all"],
        weight=1.1,
    ),
    # ── COMMUNICATION ──────────────────────────────────────────────────────────
    Rule(
        id="rambling",
        name="Answer Too Long",
        description=(
            "Answer exceeds ~2 minutes (120 seconds) without the interviewer "
            "cutting in. Rambling signals inability to prioritize. "
            "Fix: aim for 90 seconds. Use STAR to force structure. "
            "If you notice you're still in Situation after 30 seconds, skip ahead."
        ),
        category="communication",
        applies_to=["all"],
        weight=0.9,
    ),
    Rule(
        id="filler_spike",
        name="Excessive Filler Words",
        description=(
            "Filler words (um, uh, like, basically, sort of, you know) "
            "exceed 3 per minute in this segment. High filler rates signal "
            "nervousness or unprepared thinking. "
            "Fix: pause silently instead of filling. A 2-second pause sounds "
            "confident; a stream of 'um um um' does not."
        ),
        category="communication",
        applies_to=["all"],
        weight=0.8,
    ),
    Rule(
        id="no_ownership",
        name="No Clear Ownership",
        description=(
            "Uses 'we' throughout without clarifying personal contribution. "
            "Interviewers can't tell if the candidate led or just participated. "
            "Fix: lead with 'I' for your actions: 'I designed the schema, "
            "I owned the migration. The team then...' Reserve 'we' for team outcomes."
        ),
        category="communication",
        applies_to=["behavioral"],
        weight=1.1,
    ),
    # ── SENIORITY SIGNALS ──────────────────────────────────────────────────────
    Rule(
        id="no_scale_thinking",
        name="No Scale / Growth Thinking",
        description=(
            "Answer focuses only on the current state with no mention of "
            "future scale, growth, or what would break at 10x load. "
            "Senior engineers always ask 'what happens when this grows?' "
            "Fix: add 'At 10x load, the bottleneck would be X, so I designed "
            "for Y from the start' or 'The next scaling challenge would be Z'."
        ),
        category="seniority_signal",
        applies_to=["system_design", "coding_discussion"],
        weight=1.2,
    ),
    Rule(
        id="no_stakeholder_mgmt",
        name="No Stakeholder Management",
        description=(
            "Leadership story is purely technical — no mention of aligning "
            "stakeholders, managing up, navigating disagreement, or influencing "
            "without authority. L5+ candidates must demonstrate this. "
            "Fix: include how you got buy-in: 'I had to convince the PM to delay "
            "the launch by 2 weeks. I presented data showing...'."
        ),
        category="seniority_signal",
        applies_to=["behavioral"],
        weight=1.2,
    ),
    Rule(
        id="no_mentoring_signal",
        name="No Team Growth / Mentoring",
        description=(
            "Senior/staff answer misses opportunity to mention growing the team: "
            "mentoring, code review culture, design doc standards, or elevating "
            "junior engineers. L6 expectations require this. "
            "Fix: 'I also used this project to mentor X — I had them own the "
            "migration script with my review, which helped them grow into...'."
        ),
        category="seniority_signal",
        applies_to=["behavioral"],
        weight=1.1,
    ),
    # ── NEGOTIATION ────────────────────────────────────────────────────────────
    Rule(
        id="weak_anchor",
        name="Weak First Anchor",
        description=(
            "First number named was too low (below market) or reactive "
            "(responded to their number without anchoring first). "
            "Whoever anchors first sets the range. "
            "Fix: anchor 15-20% above target. If they anchor first, "
            "ignore it and reanchor: 'Based on my research, I'm targeting X'."
        ),
        category="seniority_signal",
        applies_to=["negotiation"],
        weight=1.3,
    ),
    Rule(
        id="early_concession",
        name="Early Concession",
        description=(
            "Gave ground on a key dimension (salary, equity, start date) "
            "before receiving a counter-argument or new information. "
            "Conceding too early signals low confidence and leaves money on the table. "
            "Fix: respond to pushback with questions, not concessions: "
            "'What's driving that constraint?' before moving your position."
        ),
        category="seniority_signal",
        applies_to=["negotiation"],
        weight=1.2,
    ),
]

# ── Lookup tables ──────────────────────────────────────────────────────────────

RULES_BY_ID: dict[str, Rule] = {r.id: r for r in RULES}
RULE_IDS: list[str] = [r.id for r in RULES]


def rules_for_question_type(question_type: str) -> list[Rule]:
    """Return rules that apply to a given question type."""
    return [r for r in RULES if "all" in r.applies_to or question_type in r.applies_to]


# ── Cached prompt prefix text ──────────────────────────────────────────────────
# This block (~1300 tokens) is sent as the Anthropic "cache" control prefix.
# After the first call, Anthropic caches it for ~5 minutes at $0.30/MTok (90% off).

RUBRIC_PROMPT_PREFIX = """You are an interview scoring engine. Evaluate interview answers against the rubric below.

=== SCORING RUBRIC (15 rules) ===

STRUCTURE RULES (does the answer tell a clear story with evidence?):
  no_star_structure    — Answer lacks Situation/Task/Action/Result framing.
  missing_result       — Actions described but no outcome stated.
  result_not_specific  — Outcome exists but is vague ("improved performance").
  missing_metrics      — Zero quantifiable data points (numbers, %, $, times).

DEPTH RULES (does the answer show engineering maturity?):
  no_tradeoff          — Decision presented without alternatives or tradeoff discussion.
  no_assumptions       — System design answer missing stated scale assumptions.
  shallow_followup     — Answer became vague when probed deeper.

COMMUNICATION RULES (is the answer crisp and ownable?):
  rambling             — Answer exceeded ~2 minutes without structure.
  filler_spike         — Filler words (um/uh/like/basically) exceed 3 per minute.
  no_ownership         — Uses "we" throughout with no clarification of personal role.

SENIORITY SIGNAL RULES (does the answer sound like L5/L6?):
  no_scale_thinking    — No mention of future scale, growth, or what breaks at 10x.
  no_stakeholder_mgmt  — Leadership story missing stakeholder alignment or influence.
  no_mentoring_signal  — Senior answer missing team growth or mentoring examples.

NEGOTIATION RULES (applies to negotiation sessions only):
  weak_anchor          — First number too low or reactive (responded rather than anchored).
  early_concession     — Gave ground before receiving counter-argument.

=== LEVEL EXPECTATIONS ===

L4 (Senior): STAR structure present, at least 1 metric, owns outcome clearly.
L5 (Staff): All L4 + tradeoffs discussed, scale thinking present, stakeholder awareness.
L6 (Principal): All L5 + mentoring/team growth, systemic thinking, org-level impact.

=== OUTPUT FORMAT ===

Return a JSON object with this exact schema:
{
  "overall_score": <integer 0-100>,
  "confidence": <"high" | "medium" | "low">,
  "rules_triggered": [
    {
      "rule": <rule_id string>,
      "confidence": <"strong" | "weak">,
      "evidence": {
        "start_ms": <integer milliseconds from session start>,
        "end_ms": <integer milliseconds from session start>
      },
      "fix": <specific 1-2 sentence fix suggestion>,
      "impact": <string like "+12 to Structure score">
    }
  ],
  "categories": {
    "structure": <integer 0-100>,
    "depth": <integer 0-100>,
    "communication": <integer 0-100>,
    "seniority_signal": <integer 0-100>
  },
  "level_assessment": {
    "l4": <"pass" | "borderline" | "fail">,
    "l5": <"pass" | "borderline" | "fail">,
    "l6": <"pass" | "borderline" | "fail">,
    "gaps": [<string describing what's missing for next level>]
  },
  "diff_versions": {
    "minimal": {
      "text": <string — 1-2 sentence patch, keep everything else identical>,
      "changes": [{"before": <str>, "after": <str>, "rule": <rule_id>, "impact": <str>}],
      "estimated_new_score": <integer>
    },
    "medium": {
      "text": <string — full restructured answer>,
      "changes": [{"before": <str>, "after": <str>, "rule": <rule_id>, "impact": <str>}],
      "estimated_new_score": <integer>
    },
    "ideal": {
      "text": <string — what the perfect answer would sound like at target level>,
      "changes": [{"before": <str>, "after": <str>, "rule": <rule_id>, "impact": <str>}],
      "estimated_new_score": <integer>
    }
  },
  "memory_hints": {
    "skill_signals": [{"skill": <str>, "direction": <"positive" | "negative">, "note": <str>}],
    "story_detected": <boolean>,
    "story_title": <string or null>,
    "communication_notes": <string or null>
  }
}

CRITICAL RULES FOR EVIDENCE:
- evidence.start_ms and end_ms are timestamps from the session transcript.
- ONLY reference timestamps that exist in the provided transcript.
- The server extracts the actual quote — do NOT generate quotes yourself.
- If you cannot pinpoint the exact span, use confidence "weak" and estimate the range.
- Do not hallucinate evidence for rules you are uncertain about.
"""
