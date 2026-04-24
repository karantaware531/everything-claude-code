# runtime.md — Execution Model (v5.7)

> The canonical loop every non-trivial task in this system MUST follow.
> Enforced by `.claude/CLAUDE.md` §6 and `.claude/rules/routing.md`.
>
> **v5.7**: `/lead-agent` is the MANDATORY entry point. Planning Council runs
> BEFORE the planner touches anything. Ship Council retains full v5.5 veto
> scope on executor output.
> **v5.5**: orchestrator agent retired; main Claude Code session is the Lead Agent.
> **v5.2**: Wiki retired → Graphify (`graphify-out/graph.json`) + `.claude/notes/`.
> **v5.4**: `.claude/rules/*.md` path-scoped; `.claude/skills/*/SKILL.md` workflows.

---

## The Loop (v5.7)

```
    user request
         │
         ▼
    /lead-agent
         │
         ▼
   ┌─────────┐   ┌──────────┐   ┌──────────────┐   ┌──────┐   ┌──────────┐   ┌─────────┐
   │ CONTEXT │──▶│ STRATEGY │──▶│  PLANNING    │──▶│ PLAN │──▶│ SIMULATE │──▶│ EXECUTE │
   └─────────┘   │  MATCH   │   │  COUNCIL     │   │(thin │   └──────────┘   └────┬────┘
                 └──────────┘   │  (mandatory) │   │synth)│                       │
                                └──────────────┘   └──────┘                       │
                                       │                                          │
                                       │  SPEC.md (binding)                       │
                                       │  TASK_ASSIGNMENTS.md                     │
                                       │  CONSENSUS.md                            │
                                       ▼                                          │
                                (specialists fan-out)                             │
                                                                                  │
                                         ┌────────────────────────────────────────┤
                                         ▼                                        │
                                   ┌──────────┐    ┌──────────┐                   │
                                   │  CRITIC  │──▶ │EVALUATOR │                   │
                                   └──────────┘    └────┬─────┘                   │
                                                        │                         │
                                              pass ◀────┴──▶ fail                 │
                                                │             │                   │
                                                ▼             ▼                   │
                                         ┌────────────┐   retry or                │
                                         │  REFLECT   │   Ship Council            │
                                         │  (notes/)  │   escalate                │
                                         └─────┬──────┘                           │
                                               │                                  │
                                               ▼                                  │
                                         ┌──────────┐                            │
                                         │graphify_ │                            │
                                         │  update  │                            │
                                         └────┬─────┘                            │
                                              │                                  │
                                              ▼                                  │
                                        ┌──────────┐                            │
                                        │  LOG +   │◀───────────────────────────┘
                                        │ SCORING  │
                                        └──────────┘
```

---

## Explicit Call Graph (v5.7)

```
user
 └─▶ /lead-agent <task>
       │
       ├─▶ Lead Agent (main Claude Code session)
       │     reads: .claude/CLAUDE.md, .claude/rules/routing.md,
       │            .claude/registry.json, AGENTS.md, SPECIALISTS.md,
       │            .claude/skills/lead-agent/SKILL.md
       │
       ├─▶ python .claude/core/context_engine.py --task "<task>" --format json
       │     emits provenance-tagged context bundle; hash → context_ref
       │
       ├─▶ goal_keeper
       │     reads .claude/memory/goals_state.json
       │     anchors task to current_goal / active_subgoal
       │
       ├─▶ meta_controller
       │     python .claude/core/autonomy_controller.py --task --uncertainty --risk
       │     → decides autonomy tier 1-4 (domain_policies.yaml applied)
       │
       ├─▶ graphify_agent (action=query)
       │     scans graphify-out/graph.json for matching strategies
       │     if confidence ≥ 0.8 and trials ≥ 3 → seed Planning Council
       │
       ├─▶ PLANNING COUNCIL (v5.7 — mandatory, via .claude/skills/lead-agent)
       │     1. CLASSIFY     Lead Agent assigns task-type + domain
       │     2. ROSTER       pick 6-9 specialists from SPECIALISTS.md (4-core min)
       │     3. PERSPECTIVES parallel fan-out via Task tool; each writes
       │                     .claude/notes/planning-council/<slug>/perspectives/<role>.md
       │     4. DEBATE       debate_moderator reconciles contradictions
       │                     → .claude/notes/planning-council/<slug>/DEBATE.md
       │     5. SPEC         synthesize → SPEC.md (BINDING)
       │     6. ASSIGN       DAG with best-fit specialist per node → TASK_ASSIGNMENTS.md
       │     7. CONSENSUS    specialists sign off → CONSENSUS.md
       │     8. SPEC REVIEW  critic + evaluator audit SPEC (not code)
       │                     CRITICAL/HIGH → loop back to step 4
       │
       ├─▶ planner (cognitive)
       │     THIN synthesis of SPEC + TASK_ASSIGNMENTS → DAG
       │     (no fresh authoring — constrained to Planning Council output)
       │
       ├─▶ python .claude/core/execution_engine.py --simulate
       │     (abort if risk=high)
       │
       └─▶ execution_engine.run(dag)
             └─▶ per node (topological):
                   1. agent_selector.select(capability, task, caller)
                        ε-greedy 10% for cold-start agents
                        utility tie-break (core/utility.py) when scores ≤ 0.05 apart
                   2. if chosen is None AND SPEC doesn't pin owner → factory handoff
                        factory creates agent (budget ≤ 2)
                        registry_manager ratifies
                   3. execution agent invoked
                        code_agent | research_agent | tool_executor |
                        graphify_agent | voltagent-<specialist>
                        tool_executor consults tool_registry + policy_guard
                   4. context_engine.update_context(step_result)
                   5. critic (governance; red-team)
                   6. evaluator (governance; pass/fail + uncertainty)
                        │
                        ├─pass─▶ reflection (writes notes/strategies|experience)
                        │          └─▶ graphify_agent (action=update) incremental
                        │
                        └─fail─▶ SHIP COUNCIL evaluates:
                                   • CRITICAL/HIGH → block; loop back to worker
                                   • 2× failure → escalate (tier ≥ 3)
                                   • SPEC violation → re-convene Planning Council
                   7. scoring_engine.record(duration, tokens, accuracy, success, caller)
                        if caller known → trust_matrix update
                   8. observability/traces.json append

 └─▶ reflection (after task completes)
       ├─▶ writes .claude/notes/strategies/ (winning sequence)
       ├─▶ writes .claude/notes/experience/ (distilled lesson)
       ├─▶ knowledge_validator resolves AMBIGUOUS graph edges
       ├─▶ goal_keeper updates subgoal progress
       ├─▶ registry_manager (prompt amendment proposals, with evidence)
       ├─▶ pattern_extractor (at epoch boundaries — every 5+ strategies)
       └─▶ graphify_agent (action=update) → graphify-out/graph.json

 └─▶ [IF circuit breaker tripped] escalation payload → user
       Lead Agent pauses DAG, awaits user reply
```

---

## Pseudocode

```pseudo
function run(task):
    # v5.7 entry
    assert invoked_via("/lead-agent") or opt_out_applies(task)

    context  = context_engine.build_context(task)
    strategy = graphify_agent.query("strategies matching " + task_type)
    spec     = planning_council.convene(task, context, strategy)
    # spec is BINDING — deviation requires re-convene
    dag      = planner.synthesize(spec.TASK_ASSIGNMENTS)
    risk     = execution_engine.simulate(dag)

    if risk.level == "high":
        escalate(risk.issues)
        return

    breaker = CircuitBreaker(threshold=3)

    for node in dag.topological_order():
        chosen = agent_selector.select(node.capability, task, caller=node.predecessor)
        if chosen is None:
            chosen = factory.create(node.required_capability)  # budget ≤ 2

        output = invoke(chosen, node.input, context_hash=hash(context))
        critique = critic.review(output, expected=node.expected_output, spec=spec)
        verdict  = evaluator.grade(output, critique, contract=node.expected_output, spec=spec)

        scoring_engine.record(agent=chosen, ...)

        if verdict.pass:
            reflection.capture(output)                      # notes/strategies|experience
            graphify_agent.update(".claude/notes/")         # incremental
        else:
            if breaker.record_failure(chosen):
                escalate("circuit breaker on " + chosen)
                return
            if verdict.spec_violation:
                planning_council.reconvene(spec, issue=verdict.reason)
                return
            if node.retries < 2 and verdict.retryable:
                node.retries += 1
                continue
            escalate(verdict.reason)
            return

        traces.append({task_id, node, chosen, verdict})

    reflection.run(task, trace=traces.filter(task_id=task.id))
```

---

## Phase Contracts

### CONTEXT
`core/context_engine.build_context(task)`. Provenance-tagged fields; untrusted content in hard separators.

### STRATEGY_MATCH
Query `graphify_agent` for strategies matching task type. If confidence ≥ 0.8 AND trials ≥ 3, seed Planning Council.

### PLANNING_COUNCIL (v5.7 mandatory)
Skill `.claude/skills/lead-agent/SKILL.md` runs the 9-step workflow. Produces binding SPEC.md + TASK_ASSIGNMENTS.md + CONSENSUS.md at `.claude/notes/planning-council/<slug>/`. Ship Council cannot veto this ritual — only its SPEC content.

### PLAN
Thin synthesis of approved SPEC + TASK_ASSIGNMENTS → DAG. No fresh authoring.

### SIMULATE
`core/execution_engine.simulate(dag)`. Detects cycles, unreachable nodes, missing capabilities, depth violations.

### EXECUTE
Topological DAG run. Each node: selector → invoke → update_context → critic → evaluator → reflection (on pass) → scoring.

### VALIDATE (Ship Council — full v5.5 scope retained)
critic red-teams; evaluator grades. Vetoes on code quality, security bugs in implementation, performance, unnecessary code, SPEC violations, correctness, completeness, any other concern.

### REFLECT
reflection writes notes/strategies (if success) + notes/experience (if lesson-worthy). knowledge_validator resolves AMBIGUOUS edges. pattern_extractor at epoch boundaries.

### LOG
Traces + agent_history + scoring records. All writes atomic (temp → rename).

### GRAPHIFY
After every `.claude/notes/` write: `py -3 -m graphify update .claude/notes/`.

---

## Failure Modes & Responses

| Symptom | Response |
|---|---|
| Simulate reports `risk: high` | Halt; escalate with issue list |
| Evaluator rejects output twice | Retry once if `retryable`; else escalate |
| Circuit breaker trips (3× same error) | Escalate; mark agent session-unavailable |
| Factory proposes duplicate (sim ≥ 0.7) | Reuse; log `outcome: "reused"` |
| Depth > 5 | Halt; log `depth_exceeded` |
| New-agent budget (2) exhausted | Halt; suggest task split |
| Tool exceeds 60s | Kill; log `tool_timeout` |
| AMBIGUOUS graph edge on touched concept | knowledge_validator proposes resolution; reflection pauses until resolved |
| policy_guard denies action | Abort node; log `policy_violation` |
| .md written to `memory/**` | Hook reverts; log `karpathy_invariant_violation`; escalate |
| Executor violates SPEC | Re-convene Planning Council |
| Planning Council specialist returns empty perspective | Retry once with sharper prompt; else proceed + log missing-perspective |
| User skips `/lead-agent` for non-trivial task | Lead Agent refuses unless opt-out applies |

---

## Invariants

At all times:

1. `agent_validator.py --self-test` passes.
2. `test_runner.py` reports 44/44.
3. `harness_audit.py` reports ≥ 8.0/10 across 7 categories.
4. `find .claude/memory -name '*.md'` empty (Karpathy invariant).
5. Every `.claude/notes/` file has valid frontmatter per `.claude/rules/notes.md`.
6. Every hook command in `settings.json` uses `$CLAUDE_PROJECT_DIR` (check #42).
7. `policy_guard` consulted before every write/shell/network action.
8. Every invocation produces a protocol record in `observability/traces.json`.
9. Every constitution/policy amendment logged to `memory/logs.json` with tier ≥ 4.
10. Every non-trivial task starts with `/lead-agent` (v5.7).

---

## References

- Constitution: `.claude/CLAUDE.md` (v5.7)
- Routing: `.claude/rules/routing.md`
- Planning Council: `.claude/skills/lead-agent/SKILL.md`
- Planning Council concept: `.claude/notes/concepts/planning-council.md`
- v5.7 Council decision: `.claude/notes/consensus/v5.7-mandatory-planning-council.md`
- Full version history: `.claude/notes/concepts/agentic-os-history.md`
