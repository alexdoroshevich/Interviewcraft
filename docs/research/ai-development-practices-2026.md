# AI-Assisted Development Practices — 2026 Reference

Research conducted April 2026. Sources: [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code), [obra/superpowers](https://github.com/obra/superpowers), official Claude Code documentation, post-leak analysis sources.

---

## 1. Claude Code Configuration — What's Official vs. Invented

### Verified official patterns (April 2026)

| Pattern | Status | Notes |
|---------|--------|-------|
| Skills at `.claude/skills/` | ✅ Official | Each skill = folder with `SKILL.md` + optional `scripts/` |
| `context: fork` for isolated subagents | ✅ Official | Correct isolation keyword |
| `ultrathink` keyword for high effort | ✅ Official | Triggers extended thinking |
| `effortLevel: high` in settings.json | ✅ Official | Global default, avoids per-prompt `ultrathink` |
| `.claude/commands/` | ⚠️ Legacy | Still works, but `.claude/skills/` is the current standard |
| Hooks auto-discovered from `.claude/hooks/` | ❌ Wrong | Hooks are configured in `settings.json` only; scripts can live anywhere |
| `references/` subdirectory in skills | ⚠️ Invented | Not in official docs, harmless but non-standard |

### Hook events available (full list)

`PreToolUse`, `PostToolUse`, `PermissionDenied`, `SessionStart`, `SessionEnd`, `Stop`, `SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`

### Settings fields worth knowing

```json
{
  "effortLevel": "high",
  "autoMemoryEnabled": true,
  "hooks": { ... }
}
```

---

## 2. Agent Architecture Patterns (2026)

### Specialization over generalization

The most effective Claude Code setups use **narrowly scoped agents** rather than one general-purpose agent. Each agent should have:
- A specific domain (backend, frontend, voice pipeline, security, etc.)
- Restricted tool set (read-only agents can't edit; implementers can't push)
- Project-specific invariants embedded in the prompt (table schemas, dependency pins, gotchas)
- Model selection matched to task complexity

**Model allocation principles:**
- Opus → architecture decisions, adversarial verification, security review, deep reasoning
- Sonnet → implementation, code review, test creation, orchestration
- Haiku → scoring, diff analysis, memory extraction, high-volume low-stakes tasks

### Useful agent types beyond the obvious

| Agent | Purpose | Key trait |
|-------|---------|-----------|
| `breaker` | Adversarial — tries to break features after implementation | Opus; read-only; circuit-breaker at N critical bugs |
| `ci-review` | Orchestrator — runs code-review + logging-review + test-analysis concurrently | Weighted grading formula; spawns sub-agents |
| `spec-reviewer` | Checks if implementation matches requirements BEFORE code quality review | Adversarial posture: "implementer finished suspiciously quickly — verify everything independently" |
| `debugger` | Systematic 4-phase debugging protocol | Root Cause → Pattern Analysis → Hypothesis Testing → Fix |
| `loop-operator` | Autonomous task loops with stall detection + cost budgets | Detects consecutive checkpoint failures; reduces scope on repeated failure |

### Two-stage review (Superpowers pattern)

Single-pass code review conflates "built it correctly" with "built the right thing." Two-stage separates them:

1. **Spec-compliance review**: Did the implementation match requirements? Catches scope drift, missing requirements, over-engineering.
2. **Code-quality review**: Is what was built well-made? Catches bugs, patterns, maintainability.

Agents are prone to building the wrong thing correctly. The spec reviewer catches this before the quality reviewer runs.

---

## 3. Hook-Driven Behavioral Guardrails

### The key insight

Instructions in CLAUDE.md and system prompts degrade over long sessions due to context compaction. **Hooks are persistent constraints that survive compaction.** Use hooks for rules that must never be violated; use instructions for everything else.

### High-value hook patterns

**Config protection** (PreToolUse on Write/Edit):
Blocks modifications to linter/formatter configs (`ruff.toml`, `pyproject.toml` lint sections, `tsconfig.json`, `.eslintrc*`). Forces the agent to fix source code rather than weakening quality gates.

```json
{
  "PreToolUse": [{
    "matcher": "Write|Edit",
    "hooks": [{
      "type": "command",
      "command": "...",
      "description": "Block linter config modifications"
    }]
  }]
}
```

**Destructive command blocker** (PreToolUse on Bash):
Block `rm -rf`, `git push --force`, `git reset --hard`, `DROP TABLE`, `TRUNCATE` at the hook level — not just in instructions.

**Branch guard** (PreToolUse on Bash):
Deny `git push origin main|master` — enforce feature branch → PR workflow at the tool level.

**Session memory** (SessionStart + SessionEnd):
On `SessionEnd`: parse transcript JSONL, extract structured summary (files changed, decisions, current branch), write to dated session file.
On `SessionStart`: load most recent session summary and inject into context. Eliminates cold-start problem.

**Strategic compact suggester**:
Count tool invocations per session; suggest `/compact` every N calls. Strategic compaction preserves better context than hitting the limit.

---

## 4. Structured Agent Escalation Protocols (2026)

The 2025 pattern: agent succeeds or fails; human intervenes on failure.

The 2026 pattern: structured status codes with defined handler logic.

**Four-status implementer protocol** (from obra/superpowers):
- `DONE` — implementation complete, tests pass
- `DONE_WITH_CONCERNS` — complete but reviewer should read the concerns before proceeding
- `NEEDS_CONTEXT` — blocked on missing information, specifies what is needed
- `BLOCKED` — cannot proceed; triggers model upgrade or task decomposition, not retry

**Systematic debugging escalation:**
- After 3 failed fixes for the same root cause: **stop and question the architecture**
- Do not retry the same approach; diagnose whether the architecture assumption is wrong
- Multi-component systems (async pipelines, WebSocket chains) require backward tracing, not forward patching

**Do not trust agent self-reports:**
Agents completing tasks suspiciously quickly should be verified independently. The completion claim is not evidence of correctness. Verify with fresh tool runs, not by reading the agent's summary.

---

## 5. Continuous Learning Infrastructure (ECC v2.1)

The emerging pattern for production AI-assisted codebases: automated observation → extracted instincts → evolved skills.

**Observation layer**: PreToolUse/PostToolUse hooks capture every tool invocation to `observations.jsonl`.

**Pattern extraction**: Background Haiku agent analyzes captured observations for: repeated workflows, error patterns, user corrections after agent mistakes.

**Instinct format**: Atomic YAML with confidence score (0.3–0.9):
```yaml
instinct: "Always use CAST(:param AS jsonb) not ::jsonb in raw SQL"
confidence: 0.9
scope: project  # vs. global
trigger: "asyncpg + PostgreSQL JSONB"
source: correction  # vs. observation
```

**Promotion**: When the same instinct appears in 2+ projects with confidence ≥ 0.8, it promotes from project-scope to global. Via `/evolve`, clusters of related instincts become full skills.

**Why this matters**: Static skill/agent files require manual updates when you discover new patterns. The instinct system captures those patterns automatically and encodes them in a reviewable, versioned format.

---

## 6. Dynamic Contexts

Mode-specific system prompts that adjust agent behavior without changing the agent definition:

**`contexts/implement.md`**: Write code first, explain after. Prioritize working implementation over documentation.

**`contexts/debug.md`**: Systematic investigation required. No premature fixes. Follow 4-phase protocol.

**`contexts/review.md`**: Quality focus. Check for patterns, not just function. Verify against invariants.

These are injected at `SessionStart` (or via slash command) to prime the session for a specific type of work.

---

## 7. Security Considerations for AI-Assisted Development

**Prompt injection via user input is real.** In voice-based AI applications, STT transcriptions are an attack surface. A user can say phrases that look like system instructions. Mitigations:
- Wrap user content in structural delimiters: `<user_answer>...</user_answer>`
- Never concatenate raw user input into system prompt sections
- Apply the same sanitization to any user-controlled input reaching an LLM (chat messages, file uploads, OCR output, voice transcriptions)

**Secrets in system prompts are extractable.** Treat any value in a system prompt as potentially readable by a determined user. Never put API keys, internal URLs, or pricing information in system prompts.

**Only install Claude Code from the official installer.** After the March 2026 source leak, malicious packages claiming to be Claude Code tools appeared on npm. Use `curl` or `irm` installer paths only.

**Agent tool isolation matters.** Read-only agents (reviewers, analyzers) should not have `Write`, `Edit`, or `Bash` in their tool set. This is enforced in settings, not instructions — instructions can be ignored, tool grants cannot.

---

## 8. Key Repository References

| Repository | What it offers |
|------------|---------------|
| [affaan-m/everything-claude-code](https://github.com/affaan-m/everything-claude-code) | 38 specialized agents, hook memory/continuous learning system (v2.1), FastAPI/Next.js templates, config protection hooks, quality gate pipelines |
| [obra/superpowers](https://github.com/obra/superpowers) | Battle-hardened workflow processes: SDD pattern, two-stage review, systematic debugging, structured escalation, writing plans with no placeholders |
| [rohitg00/awesome-claude-code-toolkit](https://github.com/rohitg00/awesome-claude-code-toolkit) | Production hooks: destructive command blocker, branch guard, `block-no-verify` |
| [FlorianBruniaux/claude-code-ultimate-guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide) | Security-focused: 24 CVEs in Claude Code, 655 malicious skill patterns to watch for, MCP vetting checklist |
| [nblintao/awesome-claude-code-postleak-insights](https://github.com/nblintao/awesome-claude-code-postleak-insights) | Post-leak analysis, 3-layer context compression, AutoDream memory architecture |
