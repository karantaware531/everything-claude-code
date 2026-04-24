---
domain: concepts
title: Planning Council (v5.7 — Mandatory)
status: active
supersedes: (none; additive to Ship Council)
entry_command: /lead-agent
related:
  - .claude/rules/routing.md
  - .claude/skills/lead-agent/SKILL.md
  - .claude/commands/lead-agent.md
  - .claude/notes/consensus/v5.7-mandatory-planning-council.md
---

# Planning Council — Design Doc (v5.7)

## Problem

v5.5–v5.6 had **Ship Council** (critic + evaluator + security + reflection + knowledge_validator) as a **post-execution** veto gate. But the **plan itself** had no council:

- `planner` wrote DAGs largely solo.
- `strategy_explorer` generated K candidate DAGs but didn't consult specialists.
- `debate_moderator` only fired on disagreement (reactive, not proactive).
- No architectural / security / performance / QA / design / product / data / dev voice was forced BEFORE executors touched code.

Result: specs shipped with blind spots (cardinality DoS, perf regression, poor data model, missing test strategy, UX ambiguity). Ship Council caught them — but at the cost of full loop-backs (~80k output tokens each, per case-study:sliding-window-rate-limiter).

## Solution — Mandatory Planning Council

A **pre-execution** council of 6–9 domain specialists, entered via `/lead-agent <task>`:

1. Lead Agent classifies task → selects specialist roster from SPECIALISTS.md.
2. Each specialist produces a PERSPECTIVE.md in parallel (concerns, requirements, red flags, must-haves).
3. `debate_moderator` mediates contradictions → emits disagreement log.
4. Specialists converge on a single SPEC.md.
5. Specialists emit TASK_ASSIGNMENTS.md — a DAG where each node names the best-fit specialist per SPECIALISTS.md.
6. Ship Council's `critic` + `evaluator` lightweight-review the SPEC (not executor output — the plan itself).
7. Only then does planner hand the approved DAG to executors.

Ship Council **cannot veto the Planning Council ritual itself** — but retains FULL v5.5 veto power on everything executors subsequently produce (code quality, security bugs, performance, unnecessary code, SPEC violations, correctness, and any other concern). Planning Council reduces the frequency of "wrong approach" loop-backs; it does not narrow Ship Council's scope when an issue IS found in the implementation.

## Default specialist roster (task-adaptive)

User-requested explicit voices:

| Role | Default specialist / skill | Substitute |
|---|---|---|
| Architecture | `voltagent-qa-sec:architect-reviewer` | `engineering:architecture` skill |
| Performance | `voltagent-qa-sec:performance-engineer` | `voltagent-data-ai:database-optimizer` |
| Security | `voltagent-qa-sec:security-auditor` | `voltagent-qa-sec:penetration-tester` (offensive) |
| QA / Test strategy | `voltagent-qa-sec:qa-expert` | `voltagent-qa-sec:test-automator` + `engineering:testing-strategy` skill |
| Data engineering | `voltagent-data-ai:data-engineer` | `voltagent-data-ai:ml-engineer` (ML) |
| Design / UX | `design:design-critique` + `design:design-system` skills | `voltagent-dev-exp:documentation-engineer` (fallback) |
| Product | `voltagent-research:project-idea-validator` + `product-management:write-spec` skill | `voltagent-research:market-researcher` |
| Development | `voltagent-lang:<lang>-pro` (task language) | `code_agent` |
| Docs / Spec clarity | `voltagent-dev-exp:documentation-engineer` | — |

Lead Agent picks 6-9 of these based on task classification (see `.claude/skills/lead-agent/SKILL.md` §Roster selection).

## Workflow (canonical, v5.7)

```
/lead-agent "<task>"
  │
  ▼
1. CLASSIFY           Lead Agent assigns task-type + detects domain
  │
  ▼
2. ROSTER             Select 6–9 specialists per task classification
  │
  ▼
3. PERSPECTIVES       Parallel fan-out (Task tool); each writes perspectives/<role>.md
  │
  ▼
4. DEBATE             debate_moderator reconciles contradictions; emits disagreement log
  │
  ▼
5. SPEC               Synthesize perspectives + debate → SPEC.md
  │
  ▼
6. ASSIGN             Map each SPEC requirement to DAG node + best-fit specialist → TASK_ASSIGNMENTS.md
  │
  ▼
7. CONSENSUS          All specialists sign off (or dissent recorded); CONSENSUS.md
  │
  ▼
8. SPEC PRE-REVIEW    critic + evaluator audit SPEC (not code — the plan)
  │
  ▼
9. HANDOFF            Approved SPEC + TASK_ASSIGNMENTS → planner → executor layer
  │
  ▼
10. EXECUTE           Executors bound to SPEC; deviation triggers re-convene
  │
  ▼
11. SHIP COUNCIL      Post-exec veto on (a) SPEC violation, (b) new info, (c) missed security
```

## Integration with existing loop

**v5.5 loop**:
```
CONTEXT → STRATEGY_MATCH → PLAN → SIMULATE → EXECUTE → CONSENSUS_COUNCIL → REFLECT → LOG
```

**v5.7 loop**:
```
/lead-agent invoked
  │
  ▼
CONTEXT → STRATEGY_MATCH → PLANNING_COUNCIL → PLAN → SIMULATE → EXECUTE → SHIP_COUNCIL → REFLECT → LOG
                           └──────────┬─────────┘
                     (mandatory; produces binding SPEC)
```

`PLAN` stage is now a THIN synthesis of the Planning Council output (not fresh authoring).
`SHIP_COUNCIL` (renamed from `CONSENSUS_COUNCIL` in docs for clarity) is narrowed — fewer loop-backs because specialists pre-approved the plan.

## Opt-out conditions (narrow)

Mandatory by default. Skipped only when:
- Trivial lookup / read-only research → `research_agent` directly.
- `/hotfix` emergency → user-invoked, logged as `policy_amendment`.
- CI batch in `dontAsk` mode with pre-approved allowlist.
- User explicitly says "quick fix" or "just do X" and task is single-file + no public contract change.

Any other non-trivial task MUST pass through `/lead-agent`.

## Authority hierarchy

```
/lead-agent SPEC.md (Planning Council approved)
  │
  ├─ BINDING on planner, decomposer, executors
  │
  ├─ Ship Council retains FULL v5.5 veto on executor output:
  │    - Code quality (bugs, logic errors, unnecessary code)
  │    - Security bugs in implementation
  │    - Performance issues / regressions
  │    - SPEC violation (executor strayed)
  │    - Correctness / completeness
  │    - New info (genuine discovery)
  │    - Missed security (specialist blind spot)
  │    - Any other critic / evaluator / security / knowledge_validator concern
  │
  └─ Deviation requires:
       a. Re-convene Planning Council (if scope changes), OR
       b. Tier-3 user override (logged)
```

## Cost awareness

Planning Council adds ~6-9 parallel specialist calls + 1 debate round + 1 SPEC synthesis + 2 SHIP council pre-reviews per task.

**Overhead**: ~2–4 min wall-clock, ~40k input tokens (context reuse), ~8k output tokens.

**Saved**: empirical 1 full Ship Council loop-back = ~80k output tokens. Preventing even 50% of loop-backs pays the overhead back 5x.

Net positive for tasks > tier 2. For tier-1 tasks, opt-out conditions apply.

## Failure modes

| Failure | Response |
|---|---|
| Specialist produces empty/trivial perspective | Retry once with sharper prompt; else proceed + log missing-perspective warning |
| Persistent disagreement (2 debate rounds) | Escalate to user (tier 3); save partial CONSENSUS.md |
| SPEC rejected by critic/evaluator | Loop back to step 3 (re-run contested perspectives only) |
| Budget exceeded on perspective fan-out | Shrink to 4-core (architect, security, qa, dev); log budget_adjustment |
| User tries to skip `/lead-agent` | Lead Agent refuses (unless opt-out condition met) and surfaces this doc |

## Not in scope for v5.7

- Automated perspective weighting (all specialists equal).
- Cross-task spec deduplication (graphify handles post-hoc).
- Real-time specialist voting UI.
- Planning Council for sub-DAG nodes (runs at task root only).
- Executing SPEC changes mid-flight (re-convene instead).

## References

- Constitution §5 — Agent Government + Consensus Council (Ship Council)
- Constitution §5b — Planning Council (v5.7 amendment)
- SPECIALISTS.md — routing map
- `.claude/skills/lead-agent/SKILL.md` — the workflow
- `.claude/commands/lead-agent.md` — slash command
- `.claude/agents/cognitive/debate_moderator.md`
- `.claude/notes/consensus/v5.7-mandatory-planning-council.md`
