# /lead-agent

**v5.7 mandatory entry point.** Invokes the Planning Council skill for any non-trivial task.

## Usage

```
/lead-agent <task description>
```

Examples:
- `/lead-agent build a rate-limit middleware for our FastAPI service`
- `/lead-agent design the multi-tenant schema for the billing module`
- `/lead-agent migrate the auth system from JWT to PASETO`
- `/lead-agent refactor the ingestion pipeline to batch mode`

## What happens

1. Lead Agent classifies the task.
2. Assembles 6-9 specialists from SPECIALISTS.md (architect, performance, security, qa, data, design, product, dev, docs — task-adaptive).
3. Fan-out perspectives in parallel.
4. `debate_moderator` reconciles contradictions.
5. Synthesizes SPEC.md + TASK_ASSIGNMENTS.md.
6. Specialists sign off → CONSENSUS.md.
7. Ship Council's critic + evaluator pre-review the SPEC.
8. Approved SPEC + DAG hand off to executors.

All artifacts persist at `.claude/notes/planning-council/<task-slug>/`.

## When NOT to use

Narrow opt-outs (Lead Agent will surface this list if unsure):
- Trivial read-only lookup / research → use `research_agent` directly.
- `/hotfix` emergency path → single-line, single-file, behavior-preserving.
- CI batch in `dontAsk` mode with pre-approved allowlist.

Every other non-trivial task: **mandatory**. Ship Council cannot veto the ritual itself.

## Why mandatory

Post-exec Ship Council re-runs cost ~80k output tokens each (empirical from case-study:sliding-window-rate-limiter). Planning Council frontloads specialist debate at ~8k tokens. Preventing even 50% of Ship Council loop-backs pays the overhead back 5x.

## Full workflow

See `.claude/skills/lead-agent/SKILL.md`.

## Related

- `/council` — ad-hoc 4-voice anti-anchoring (different; advisory only).
- `/explore` — strategy_explorer K-candidate DAG generation (no specialist council).
- `/verify` — post-exec verification.
- `.claude/notes/concepts/planning-council.md` — full design rationale.
