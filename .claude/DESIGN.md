# Claude Code Agent Topology - Design Decisions

This document explains the .claude/ architecture: why each agent exists,
what model and permissions it has, and how agents relate to each other.

---

## Agent Topology

```
architect (Opus, read-only) -- designs features, evaluates ADRs
  |
  +-- implementer (Sonnet) -- lead dev, handles 80% of all tasks
  +-- backend-specialist (Sonnet) -- deep backend domain context
  +-- frontend-specialist (Sonnet) -- deep frontend domain context

  implementer output verified by:
  +-- breaker (Opus, read-only) -- adversarial testing after each feature
  +-- spec-reviewer (Sonnet, read-only) -- spec compliance + code quality

  ci-review (Sonnet) orchestrates concurrently:
  +-- code-review (Sonnet) -- 50% weight
  +-- logging-review (Sonnet) -- 20% weight
  +-- test-analysis (Sonnet) -- 30% weight

  voice-pipeline-specialist (Opus) -- owns the real-time voice loop
  debugger (Opus, 4-phase) -- systematic root cause analysis
  security-reviewer (Opus, plan mode) -- threat modeling, OWASP audit

  test-planner (Sonnet, plan only) --> test-creator (Sonnet, worktree isolation)
```

---

## Why Each Agent Exists

### architect (Opus, read-only, plan mode)
Used for feature design, ADR evaluation, competitive analysis, UX decisions.
Read-only because architectural work should produce recommendations, never directly
modify code. Opus is justified because strategic decisions have high leverage --
a wrong architectural choice costs weeks to undo.

### implementer (Sonnet, default permissions)
The workhorse. Sonnet is 3x cheaper than Opus with equivalent code-writing quality.
Handles 80% of development tasks. Has access to Agent tool to spawn specialists for
domain work. maxTurns=30 keeps it focused -- a task needing more than 30 turns is
a sign the task itself needs to be broken down.

### backend-specialist / frontend-specialist (Sonnet, default permissions)
Deep project-specific context for each layer. These agents carry the full table schema,
component library, and gotcha list for their domain, reducing subtle bugs like wrong
table names, JSONB mutation errors, or shadcn imports. Used when a task is clearly
scoped to one layer and domain expertise matters more than general reasoning.

### breaker (Opus, read-only, plan mode)
Adversarial verification after implementation. Opus because finding non-obvious bugs
requires the same depth of reasoning as creating them. Read-only enforces role
separation: breaker diagnoses, never fixes. If it could modify code, it might fix
symptoms instead of surfacing root causes for the implementer to address properly.

### spec-reviewer (Sonnet, read-only)
Two-stage gate: (1) did we build what was asked? (2) is the code correct?
Separate from breaker because spec compliance is a different concern from
security and edge-case analysis. Read-only -- produces a report, not code changes.

### ci-review (Sonnet, orchestrator)
Runs code-review, logging-review, and test-analysis concurrently via parallel
subagent spawns. Weighted grade: 50% code quality, 20% logging, 30% test coverage.
A single P0 security finding caps the score at 4/10 regardless of other grades.
The weights reflect relative production reliability impact.

### code-review (Sonnet, plan mode, 50 turns)
Structured P0/P1/P2 findings. The explicit rule that an empty P0 section is honest
prevents the LLM failure mode of adding spurious warnings to appear thorough.

### logging-review (Sonnet, read-only)
Focused on structlog quality -- session_id propagation, PII exposure, error
traceability. Separated from code-review because logging is a distinct failure mode
that code reviewers typically underweight. This app handles sensitive interview data,
so PII in logs is a real compliance risk.

### debugger (Opus, 4-phase protocol)
Used after 2+ failed fix attempts. Opus because diagnosis requires genuine reasoning
about system state, not pattern matching.
Protocol: (1) Reproduce -> (2) Hypothesize -> (3) Verify -> (4) Fix
The rule that 3 failed attempts should trigger architectural re-evaluation prevents
tunnel vision on a fundamentally wrong approach.

### voice-pipeline-specialist (Opus, full permissions)
The voice pipeline is the most complex part of the codebase. The tuned thresholds
(barge-in=80, debounce=4s/14s, ElevenLabs chunk=16384) were empirically measured --
changing them casually breaks user experience. Opus is used because the pipeline
has subtle timing interactions requiring deep reasoning. Full write permissions
because pipeline changes require coordinated edits across pipeline.py, interfaces.py,
and provider files simultaneously.

### test-planner / test-creator (Sonnet, separated roles)
Separated to enforce a clean planning -> implementation boundary. test-planner is
plan-mode only (cannot write test files). This forces a complete, implementation-ready
plan before any code is written. test-creator runs in a git worktree so test files
do not pollute the working tree if the agent fails partway through.

### test-analysis (Sonnet, read-only)
Analyzes existing test coverage for gaps, flaky tests, missing ownership checks.
Different from test-planner: analysis is diagnostic (what is missing from what
exists), planning is prescriptive (what should exist for new code).

### security-reviewer (Opus, plan mode)
Security analysis needs the same reasoning depth as adversarial attack construction.
Plan mode because findings should become tracked issues, not immediate code changes
that bypass review.

---

## Model Selection Rationale

| Model      | Used for                                                                     |
|------------|------------------------------------------------------------------------------|
| Opus 4.6   | architect, breaker, debugger, voice-pipeline-specialist, security-reviewer   |
| Sonnet 4.6 | implementer, backend/frontend specialist, CI pipeline agents                 |

Rule: Opus for strategic reasoning or adversarial thinking.
Sonnet for code generation and structured analysis.
Haiku is not used for agent work -- agents require reasoning, not summarization.

---

## Read-Only and Plan Mode Rationale

Read-only agents (architect, breaker, spec-reviewer): produce analysis and
recommendations only. They cannot use Write, Edit, or Bash. A reviewer that can
also fix what it found blurs accountability and bypasses implementer judgment.

Plan mode agents (test-planner, test-analysis, security-reviewer, code-review,
logging-review): can propose changes but require confirmation before executing.
Used for agents that may legitimately write a report file but should not
autonomously modify application code.

---

## Hook Design Rationale

### Config Protection (PreToolUse on Write/Edit)
Blocks edits to ruff.toml, tsconfig.json, .eslintrc*, tailwind.config.*, .bandit.toml,
and [tool.ruff/mypy/bandit] sections in pyproject.toml.
Motivation: the default failure mode when a lint error cannot be fixed is to loosen
the linter config. This hook prevents that without blocking other file edits.

### Branch Guard (PreToolUse on Bash)
Blocks git push to main/master. Enforces the feature-branch -> PR -> merge workflow.
Only fires on explicit git push commands, not on other git operations.

### Compaction Context Injection (PreCompact + PostCompact)
After /compact, the conversation loses critical constraints (JSONB mutation pattern,
asyncpg CAST syntax, migration number, audio-never-to-disk). PostCompact re-injects
these so the next interaction has the right constraints without needing full history.

### Session State Persistence (SessionEnd + SessionStart)
Saves branch, uncommitted files, recent commits, and open PRs to
.claude/sessions/last-session.json at session end. The next SessionStart injects
this as context, solving the where-was-I problem without relying on conversation history.

### Tool Count Milestone (PostToolUse)
Suggests /compact every 40 tool calls. At around 40 calls, context quality starts
degrading. This is a reminder, not a hard stop -- the developer decides when to compact.

### Auto-PR (PostToolUse on Bash git push)
After every git push to a feature branch, automatically creates a GitHub PR if one
does not exist. Detects changed file types to pre-check relevant checklist boxes:
Python files trigger lint and type-hint boxes; TypeScript files trigger npm lint boxes;
migration files trigger the alembic box. Generates How to test steps from the change scope.
Eliminates friction of manual PR creation while maintaining template quality.
