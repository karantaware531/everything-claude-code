---
domain: planning-council
purpose: Pre-execution specialist council artifacts (SPEC, TASK_ASSIGNMENTS, perspectives, consensus)
writers: debate_moderator, lead-agent skill
graphify_index: true
---

# Planning Council — Notes Domain

Mandatory pre-execution council (v5.7). Entry point: **`/lead-agent <task>`**.
Every non-trivial task produces a subdirectory here before executors touch anything:

```
.claude/notes/planning-council/<task-slug>/
├── SPEC.md                  # binding specification (Council-approved)
├── TASK_ASSIGNMENTS.md      # DAG with best-fit specialist per node
├── CONSENSUS.md             # final consensus + any dissents
└── perspectives/
    ├── architecture.md      # voltagent-qa-sec:architect-reviewer
    ├── performance.md       # voltagent-qa-sec:performance-engineer
    ├── security.md          # voltagent-qa-sec:security-auditor
    ├── qa.md                # voltagent-qa-sec:qa-expert
    ├── data.md              # voltagent-data-ai:data-engineer
    ├── design.md            # design:design-critique / design-system
    ├── product.md           # voltagent-research:project-idea-validator
    ├── development.md       # voltagent-lang:<lang>-pro
    └── docs.md              # voltagent-dev-exp:documentation-engineer
```

## Mandatory — not opt-in

Ship Council **cannot veto the Planning Council ritual itself** (v5.7 amendment).
It CAN still review the produced SPEC before executors dispatch.

**Opt-out** is narrow:
- Trivial lookup / read-only research (route to `research_agent` directly).
- `/hotfix` emergency path (user-invoked; logged).
- CI batch in `dontAsk` mode.

Every other non-trivial task MUST go through `/lead-agent`.

## Distinction from Ship Council

| Layer | When | Members | Vetoes on |
|---|---|---|---|
| **Planning Council** (pre-exec, v5.7) | BEFORE executors touch code | 6–9 specialists | SPEC content, task-assignment fit |
| **Ship Council** (post-exec, v5.5) | BEFORE output ships | critic, evaluator, security, reflection, knowledge_validator | SPEC violation, correctness, security |
| **debate_moderator** | Any stage on disagreement | 2+ agents in conflict | host only; no veto |

## Why mandatory

Empirical: pre-exec consensus reduces post-exec Ship Council re-runs.
Case-study:sliding-window-rate-limiter proved Ship Council catches real issues but at high cost (full loop-back = ~80k output tokens). Planning Council frontloads the debate → Ship Council converges faster.

## Authority chain

SPEC.md approved here = **binding contract**. Deviation requires either:
1. Re-convene Planning Council (if scope changes), OR
2. Tier-3 user override (logged as `constitution_amendment`).

Ship Council's post-exec veto is narrowed to:
- SPEC violation (executor strayed from plan).
- New info not available at planning time (genuine discovery).
- Security finding that specialists missed.

## Graphify indexing

Each SPEC.md + CONSENSUS.md carries `type: spec` / `type: consensus` front-matter.
`graphify_agent` surfaces past decisions on similar tasks — reduces cold-start debate length.
