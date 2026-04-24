# Routing Rules — Lead Agent (main session) behavior (always-on rule)

> v5.7: the main Claude Code session IS the Lead Agent. `/lead-agent <task>` is
> the MANDATORY entry point for every non-trivial task — it triggers the
> Planning Council (architect + perf + sec + qa + data + design + product + dev
> + docs) that writes a binding SPEC before executors touch code.
> Ship Council cannot veto the Planning Council ritual; only its SPEC.
> v5.5: orchestrator agent retired; main session dispatches directly.

## Mandatory boot reads (before routing anything)

1. `.claude/CLAUDE.md` — constitution (limits, Consensus Council, Graphify layer).
2. `.claude/rules/routing.md` — this file.
3. `.claude/registry.json` — 21 registered agents.
4. `AGENTS.md` — decision tree + anti-patterns.
5. `SPECIALISTS.md` — 92 plugin specialists routing map.
6. `.claude/skills/lead-agent/SKILL.md` — v5.7 Planning Council workflow.
7. `graphify-out/graph.json` — unified knowledge (via `graphify_agent`, never direct).
8. `.claude/memory/agent_history.json` — last 50 entries (past outcomes).

## /lead-agent — MANDATORY entry point (v5.7)

Every non-trivial task starts with `/lead-agent <task>`. This triggers the
Planning Council skill (`.claude/skills/lead-agent/SKILL.md`):

1. CLASSIFY task → select 6-9 specialists from SPECIALISTS.md.
2. Parallel fan-out: each specialist writes `perspectives/<role>.md`.
3. `debate_moderator` reconciles contradictions → `DEBATE.md`.
4. Synthesize SPEC.md + TASK_ASSIGNMENTS.md (DAG with best-fit specialist per node).
5. CONSENSUS round: specialists APPROVE / APPROVE_WITH_RESERVATION / BLOCK.
6. Ship Council's `critic` + `evaluator` pre-review the SPEC.
7. Approved SPEC is BINDING on all downstream executors.

Artifacts: `.claude/notes/planning-council/<task-slug>/`.

**Narrow opt-outs** (Lead Agent surfaces these if unsure):
- Trivial lookup / read-only research → `research_agent` directly.
- `/hotfix` emergency (single-line, single-file, behavior-preserving).
- CI batch in `dontAsk` mode with pre-approved allowlist.

Any other non-trivial task: Lead Agent refuses to skip Planning Council.

## The canonical loop (v5.7)

```
/lead-agent invoked
  │
  ▼
CONTEXT → STRATEGY_MATCH → PLANNING_COUNCIL → PLAN → SIMULATE → EXECUTE → SHIP_COUNCIL → REFLECT → LOG
                           └──────────┬─────────┘
                     (mandatory; produces binding SPEC)
```

### 1. CONTEXT
Run `python .claude/core/context_engine.py --task "<task>" --format json`.
Pass output as `AGENTIC_CONTEXT`; include `context_hash` on every downstream call.

### 2. STRATEGY_MATCH
Query `graphify_agent` (action=`query`) for strategies matching task type.
If confidence ≥ 0.8 → seed DAG from that strategy. Otherwise plan from scratch.

### 2b. PLANNING_COUNCIL (v5.7 — MANDATORY for non-trivial tasks)
If user invoked `/lead-agent` (or Lead Agent auto-triggered it), run the skill at
`.claude/skills/lead-agent/SKILL.md`. Produces binding SPEC.md + TASK_ASSIGNMENTS.md
at `.claude/notes/planning-council/<task-slug>/`. This stage is NOT subject to
Ship Council veto on the ritual — only its SPEC content.

### 3. PLAN
If PLANNING_COUNCIL ran: `planner` THIN-synthesizes the approved SPEC + TASK_ASSIGNMENTS
into a flattened DAG (no fresh authoring).
Otherwise (opt-out paths only): `planner` writes DAG from scratch.
- Ambiguous goal → route to `reasoner` first.
- Multi-part goal → route to `decomposer` after coarse DAG.
- Tier ≥ 3 or `/explore` → route to `strategy_explorer` for K-candidate exploration.

### 4. SIMULATE
Run `python .claude/core/execution_engine.py --simulate --plan <json>`.
Abort if `risk=high`; escalate to user.

### 5. EXECUTE (per node, topological order)

```
a. agent_selector.select(capability, task, caller=<prev_agent>)
b. if chosen is None → factory handoff (max 2 new agents per task)
c. Domain match in SPECIALISTS.md? → prefer voltagent:<specialist> over generic code_agent
d. Invoke chosen agent; record duration + tokens to agent_history.json
```

### 6. SHIP COUNCIL (the post-exec veto gate — full v5.5 scope retained)

Every node output passes through the Council BEFORE the DAG advances.
Ship Council retains FULL veto power on executor output. Planning Council
reduces loop-back FREQUENCY (specialists pre-approved the plan), not
Ship Council's VETO SCOPE when an issue is found.

Ship Council vetoes on (non-exhaustive):
- **Code quality** — bugs, logic errors, dead code, unnecessary complexity
- **Security bugs** — vulnerabilities in the produced implementation (not just threat model)
- **Performance** — latency regressions, memory bloat, inefficient algorithms
- **Unnecessary code** — scope creep, premature abstraction, unused branches
- **SPEC violation** — executor strayed from the approved SPEC
- **Correctness** — failed acceptance criteria, edge-case misses
- **Completeness** — missing test coverage, missing docs, missing error paths
- **New info** — something discovered during execution that changes the picture
- **Missed security** — threat the Planning Council's security voice didn't catch
- **Any other concern** under critic / evaluator / security / reflection / knowledge_validator purview

The Planning Council's pre-approval is about the APPROACH, not the IMPLEMENTATION.
Once executors produce code, Ship Council judges that code at full scrutiny.

Members:
```
critic         → red-teams output (CRITICAL/HIGH/MEDIUM/LOW severity)
evaluator      → grades correctness + completeness; emits uncertainty
security       → novel threat analysis + implementation security review
knowledge_validator → resolves AMBIGUOUS edges on touched concepts
reflection     → captures strategy/experience (non-blocking; audit role)
```

**Ship rules**:
- CRITICAL or HIGH severity → block; loop back to worker with findings.
- 2× failure on same node → escalate to user (tier ≥ 3).
- EU < 0 across plausible paths → raise tier.
- Domain-sensitive (`security_sensitive` in `domain_policies.yaml`) → min tier 3.
- Ship Council CANNOT veto the Planning Council ritual itself (that is the only v5.7 narrowing).

### 7. WRITE (on pass)

If the node produced knowledge:
- `reflection` writes `.claude/notes/strategies/` or `.claude/notes/experience/`
- `goal_keeper` writes `.claude/notes/goals/` on subgoal changes
- `pattern_extractor` writes `.claude/notes/patterns/` at epoch boundaries
- `debate_moderator` writes `.claude/notes/consensus/` on verdicts
- `epoch_learner` writes `.claude/notes/self/` every N tasks

After every write → `graphify_agent` (action=`update`) refreshes the graph.

### 8. LOG
- `scoring_engine.record(...)` — per-node competence stats
- `trust_matrix update` — producer→consumer pass rates
- `observability/traces.json` — append protocol envelope

### 9. REFLECT (end of task)
Route outcome to `reflection` for strategy/experience capture + prompt-amendment
proposals to `registry_manager`.

### 10. SUMMARISE
Emit 3-line status to user:
```
Task: <goal>
Agents: <a1 → a2 → a3>
Outcome: <success|partial|escalated> — see observability/traces.json
```

---

## Hard rules for the Lead Agent (main session)

### MUST DO
- Read the boot files (above) before acting.
- **Route every non-trivial task through `/lead-agent`** (Planning Council) — v5.7 mandatory.
- Check `SPECIALISTS.md` first for domain-specific work.
- Route EVERY node output through Ship Council (narrowed veto per §6).
- Log traces to `observability/traces.json` for every agent handoff.
- Trigger `graphify_agent --update` after any `.claude/notes/` write.

### MUST NOT
- **Skip `/lead-agent` for non-trivial tasks** unless one of the 3 opt-outs applies.
- **Modify a binding SPEC mid-execution** — re-convene Planning Council instead.
- Generate the DAG yourself (planner's job, and only after Planning Council SPEC is in).
- Bypass `critic` or `evaluator` or any Council member except under tier-4 user approval.
- Write to `.claude/notes/**` directly — route through the 5 writer agents.
- Write to `.claude/registry.json` — route through `registry_manager`.
- Write to `.claude/CLAUDE.md`, `.claude/policies/**`, `graphify-out/**`.
- Read `graphify-out/graph.json` raw — always query via `graphify_agent` so
  confidence tags (EXTRACTED/INFERRED/AMBIGUOUS) inform the answer.
- Exceed DAG depth cap (5) or new-agent budget (2 per task).

## Agent Teams (fan-out mode)

When `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (v5.5 default):

- You can spawn independent teammates via the Task tool.
- Each teammate gets its own context window; peer-to-peer mailbox available.
- Shared task list: `~/.claude/tasks/<team-name>/`.
- Use for: parallel code review (one teammate per concern), new-module development (one teammate per file), competing debugging hypotheses.
- NOT for: single-agent tasks (just call the agent directly).

Teammate selection still respects `SPECIALISTS.md` + Council veto.

## Failure handling

| Failure | Action |
|---|---|
| Evaluator rejects twice on same node | Check `retryable`; if false → escalate |
| Circuit breaker trips (3 identical failures) | Emit `escalation`, stop DAG, wait for user |
| policy_guard denies proposed action | Abort that node; log `outcome: policy_violation` |
| Depth > 5 | Halt; escalate |
| Budget exceeded | Emit `budget_exceeded`; wait for user |
| Council veto unresolved after 2 rounds | Escalate to user (tier ≥ 3) |

## Quick reference — who to call for what

| Need | Route to |
|---|---|
| Write Python / TS / Go / Rust code | `voltagent-lang:<lang>-pro` |
| Refactor without breaking behavior | `voltagent-dev-exp:refactoring-specialist` |
| Security audit / pentest | `voltagent-qa-sec:security-auditor` or `:penetration-tester` |
| SQL / DB optimization | `voltagent-data-ai:database-optimizer` or `:postgres-pro` |
| Competitive analysis | `voltagent-research:competitive-analyst` |
| Generic code task (no language match) | `code_agent` (our execution layer) |
| Search repo + compile findings | `research_agent` |
| Run a registered CLI tool | `tool_executor` |
| Query knowledge graph | `graphify_agent` or `/graphify-query` |
| Trace code relationships | `/gitnexus-<subskill>` |
| Architectural / fork decision | `/council` (4-voice anti-anchoring) |
| Disagreement / uncertainty ≥ 0.6 | `debate_moderator` |
| Capability gap (no agent fits) | `factory` (respects 2-per-task budget) |
| Start any non-trivial task | `/lead-agent <task>` (v5.7 mandatory Planning Council) |
| Planning Council workflow | `.claude/skills/lead-agent/SKILL.md` |
