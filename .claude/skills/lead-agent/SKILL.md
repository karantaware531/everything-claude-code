---
name: lead-agent
description: Mandatory entry point for every non-trivial task. Assembles specialist Planning Council (architecture, performance, security, QA, data, design, product, development, docs), runs debate, writes SPEC + TASK_ASSIGNMENTS, reaches consensus, then hands approved DAG to executors. Use whenever user invokes /lead-agent or asks to build/design/architect/migrate/refactor anything non-trivial.
license: MIT
compatibility: Agentic OS v5.7+ (Claude Code harness with Planning Council + Ship Council)
metadata:
  project: agentic-os
  version: "5.7"
  trigger: "/lead-agent"
  mandatory: "true"
  opt_out: "trivial lookup; /hotfix emergency; CI batch in dontAsk mode"
---

# Lead Agent — Planning Council Workflow

**This is the v5.7 mandatory entry-point skill.** Any non-trivial task goes through this flow BEFORE executors touch code.

Ship Council cannot veto this ritual. It can only review the SPEC content produced here.

## When to invoke

**Always** when user says any of:
- "build X" / "design X" / "architect X" / "migrate X"
- "refactor Y across the codebase"
- "add feature Z"
- "make a new X"
- Any request that will touch > 1 file AND is not a single-line hotfix

**User-invoked**: `/lead-agent <task description>`

**Opt-out** (narrow): the 3 conditions in frontmatter. Document the opt-out in the first response.

## §1. Classification (step 1)

Classify the task into exactly one primary type:

| Primary type | Signals |
|---|---|
| `feature-build` | "add", "build", "create", "implement" + new capability |
| `architecture` | "design system", "architect", "refactor wide", "redesign" |
| `data-pipeline` | "ingest", "ETL", "warehouse", "pipeline", "migration" (data) |
| `api-contract` | "endpoint", "API", "GraphQL", "REST", "gRPC" |
| `performance` | "optimize", "speed up", "latency", "throughput", "scale" |
| `security-hardening` | "audit", "harden", "threat model", "pentest" |
| `bugfix-wide` | "fix X across Y" (multi-file; narrow fixes bypass) |
| `product-launch` | "ship product", "v1.0", "GA" — includes UX + docs + perf |

Also detect secondary domains (a feature-build might be data-heavy + security-sensitive).

## §2. Roster selection (step 2)

Pick 6–9 specialists from SPECIALISTS.md. Hard minimum: architecture + security + qa + development (the 4-core). Add others per domain.

Default mapping:

| Task type | Default roster |
|---|---|
| `feature-build` | architect, performance, security, qa, data (if data-touch), design (if UI), product, dev, docs |
| `architecture` | architect, performance, security, qa, data, dev, docs (7) |
| `data-pipeline` | architect, performance, security, qa, data (lead), dev, docs (7) |
| `api-contract` | architect, performance, security, qa, design (API UX), product, dev, docs (8) |
| `performance` | architect, performance (lead), qa, data, dev, docs (6) |
| `security-hardening` | architect, security (lead), qa, dev, docs (5) + pentester if offensive |
| `bugfix-wide` | architect, security, qa, dev (4-core) |
| `product-launch` | ALL 9 |

Roster → agents mapping:

```
architecture     → voltagent-qa-sec:architect-reviewer
performance      → voltagent-qa-sec:performance-engineer
security         → voltagent-qa-sec:security-auditor
qa               → voltagent-qa-sec:qa-expert
data             → voltagent-data-ai:data-engineer
design           → design:design-critique skill (run inline)
product          → voltagent-research:project-idea-validator
development      → voltagent-lang:<lang>-pro (detect language)
docs             → voltagent-dev-exp:documentation-engineer
```

Announce the roster to the user in one line: `Roster: architect + perf + sec + qa + data + dev + docs (7)`.

## §3. Parallel perspective fan-out (step 3)

Create working directory: `.claude/notes/planning-council/<task-slug>/perspectives/`.
`<task-slug>` = lowercase-kebab of first 5 words of task.

Dispatch ALL specialists in parallel via the Task tool. Each gets the same prompt body + their role-specific lens:

```
# Planning Council — <role> perspective

## Task
<full task description>

## Your lens
You are the <role> voice on the Planning Council. Produce perspectives/<role>.md using the template at .claude/skills/lead-agent/templates/PERSPECTIVE_TEMPLATE.md.

Focus your lens:
- architecture → component boundaries, coupling, extensibility
- performance → latency budgets, throughput, memory, scaling cliffs
- security → threat model, attack surface, data classification, authz
- qa → test strategy, coverage, flakiness risks, verification gates
- data → schema, migrations, consistency, retention, lineage
- design → user flow, accessibility, information hierarchy
- product → user fit, viability, MVP scope, success metrics
- development → implementation feasibility, language fit, libraries
- docs → spec clarity, API documentation, changelog, migration guide

Output requirements:
- 400-800 words
- MUST-haves (hard requirements)
- SHOULD-haves (strong preferences)
- RED FLAGS (things that will break or embarrass us)
- QUESTIONS (unresolved — flag for debate)
- TASKS (units of work this perspective adds — will feed TASK_ASSIGNMENTS.md)

Do NOT write code. Do NOT implement. You are planning only.
```

All 6-9 run in ONE message with parallel Task calls.

## §4. Debate (step 4)

Read every perspective. Find contradictions (e.g., security wants mTLS, performance wants HTTP/1). Pair-contradictions go to `debate_moderator` (existing agent) for reconciliation.

Write `.claude/notes/planning-council/<task-slug>/DEBATE.md` capturing:
- Contradictions found
- Debate moderator verdict per contradiction
- Unresolved (escalate to user if ≥ 2)

## §5. SPEC synthesis (step 5)

Write `.claude/notes/planning-council/<task-slug>/SPEC.md` using `.claude/skills/lead-agent/templates/SPEC_TEMPLATE.md`.

Every MUST-have from every perspective is reflected (or explicitly deferred with rationale). SHOULD-haves are ranked. RED FLAGS become non-negotiable constraints.

## §6. Task assignments (step 6)

Write `.claude/notes/planning-council/<task-slug>/TASK_ASSIGNMENTS.md` using the template. Each DAG node carries:
- Task ID (T-01, T-02, …)
- Title
- Description
- Dependencies (other task IDs)
- Best-fit specialist (from SPECIALISTS.md)
- Acceptance criteria (ties back to SPEC section)
- Estimated budget (tokens / wall-clock)
- Risk (low / medium / high)

## §7. Consensus (step 7)

Fan-out ONE MORE round: each specialist reviews SPEC.md + TASK_ASSIGNMENTS.md and returns either:
- `APPROVE` — no dissent
- `APPROVE_WITH_RESERVATION` — reservations noted in consensus doc
- `BLOCK` — specific objection, must resolve before proceeding

Write `.claude/notes/planning-council/<task-slug>/CONSENSUS.md` using the template.

**Block rule**: any `BLOCK` requires re-debate (step 4) on that specific issue. After 2 block rounds, escalate to user.

## §8. Ship Council SPEC pre-review (step 8)

Invoke `critic` and `evaluator` (Ship Council members) with ONE narrow prompt:
```
Review .claude/notes/planning-council/<task-slug>/SPEC.md as a PLAN (not code).
- critic: red-team the plan; flag CRITICAL/HIGH/MEDIUM/LOW.
- evaluator: score completeness against task requirements; flag missing.
```

If CRITICAL or HIGH → loop back to step 4 (NOT step 3 — don't re-fan-out all perspectives).
If MEDIUM or LOW → note in SPEC §Open Risks and proceed.

## §9. Handoff (step 9)

Emit handoff message to user:
```
Planning Council complete — <task-slug>
  Roster: <N> specialists
  SPEC: .claude/notes/planning-council/<task-slug>/SPEC.md
  Tasks: <N> DAG nodes
  Consensus: <APPROVE_COUNT>/<TOTAL> approve
  Proceed? (y to hand off to executors, n to revise)
```

On user `y` (or tier 1 auto): pass SPEC + TASK_ASSIGNMENTS to `planner` (which now THIN-synthesizes rather than authoring fresh).

Then executors run per normal Lead Agent routing (`.claude/rules/routing.md`).

## §10. Ship Council (full v5.5 veto scope retained)

Post-execution Ship Council retains FULL v5.5 veto power on executor output.
Planning Council reduces loop-back FREQUENCY, not veto SCOPE.

Ship Council vetoes on (non-exhaustive):
- Code quality (bugs, logic errors, dead code, complexity)
- Security bugs in the implementation
- Performance issues / regressions
- Unnecessary code / scope creep
- SPEC violations (executor strayed)
- Correctness / completeness failures
- New info discovered during execution
- Any other critic / evaluator / security / reflection / knowledge_validator concern

Planning Council's pre-approval is about APPROACH, not IMPLEMENTATION.
Once executors produce code, Ship Council judges that code at full scrutiny.

The ONLY v5.7 narrowing: Ship Council cannot veto the Planning Council ritual
itself (you can't reject that the ritual happened — only its content).

## Graphify

After every write in this skill, trigger:
```
py -3 -m graphify .claude/notes/ --update
```

Past SPECs surface for similar future tasks — reduces cold-start debate length.

## Red flags / rationalizations to refuse

| Rationalization | Reality |
|---|---|
| "This is small, skip Planning" | If it touches > 1 file or changes a contract, it's not small. |
| "I already know what to do" | The Council isn't for you — it's for the specialists to red-team you. |
| "Specialists will say the same thing" | If they do, great — fast path. If they don't, you needed them. |
| "User is in a hurry" | `/hotfix` is the documented fast-path. `/lead-agent` is default. |
| "Ship Council will catch issues anyway" | At ~80k tokens per loop-back. Planning at ~8k. Math wins. |

## Failure recovery

If any step fails, the skill MUST:
1. Write the partial state to `.claude/notes/planning-council/<task-slug>/INCOMPLETE.md`.
2. Log to `.claude/memory/logs.json` with outcome `planning_council_incomplete`.
3. Surface the failure to the user with the opt-out options listed.

Do not silently skip to executors.
