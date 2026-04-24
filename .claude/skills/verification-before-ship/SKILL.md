---
name: verification-before-ship
description: Use BEFORE declaring any task "done", "complete", "shipped", or creating a PR. Runs the 8-point verification gate — tests, harness, SPEC compliance, graphify consistency, Ship Council sign-off, trace recorded, logs updated, git status intentional. Evidence before assertions; never claim success without this gate passing. Our own version of superpowers:verification-before-completion — extended for our Council + Graphify + Karpathy invariant.
license: MIT
compatibility: Agentic OS v5.7+ (requires Ship Council agents + Graphify + test_runner.py)
metadata:
  project: agentic-os
  version: "5.7"
  trigger: "done, complete, shipped, ready, finished, before /commit-push-pr"
  rigid: "true"
  complements: "superpowers:verification-before-completion"
---

# Verification-before-ship — evidence before assertions

**Never declare "done" without running this skill and showing its output.** If the skill blocks, the task is not done. Do not work around; do not claim partial success — block, surface, escalate.

## Why this exists (beyond `superpowers:verification-before-completion`)

superpowers' version covers tests + build + type-check + git. Ours adds:
- Ship Council sign-off (the 5 governance agents ratified the output)
- Graphify consistency (no unresolved AMBIGUOUS edges on touched concepts)
- SPEC compliance (if Planning Council produced a binding SPEC)
- Karpathy invariant (no `.md` in `memory/`)
- Observability trace recorded (audit trail exists)
- Amendment log updated (any constitution/policy change is auditable)

## The 8-point gate

### 1. Tests — 44/44

```bash
py -3 .claude/tools/test_runner.py
```
Must report `44/44 checks passed`. No exceptions.

### 2. Harness audit — ≥ 8.0

```bash
py -3 .claude/tools/harness_audit.py
```
Overall ≥ 8.0 AND verdict `PASS`. Compare to prior baseline — any category dropping > 1 point is a regression even if still passing.

### 3. SPEC compliance (if Planning Council ran)

For each AC in `.claude/notes/planning-council/<task-slug>/SPEC.md` §7:
- Verify the implementation satisfies it (show evidence: test name, file:line, output).
- Untouched AC → task not done.
- Descoped AC → re-convene Planning Council, don't silently drop.

If no SPEC (opt-out was used), document WHICH opt-out condition applied.

### 4. Ship Council sign-off

The 5 governance agents must have reviewed the final output:
- `critic` verdict (no unresolved CRITICAL / HIGH).
- `evaluator` verdict (pass + uncertainty ≤ 0.3).
- `security` verdict (if domain touched auth/io/net/fs).
- `knowledge_validator` verdict (if graph has AMBIGUOUS edges on touched concepts).
- `reflection` captured strategy/experience.

Show trace IDs for each verdict. If any absent → dispatch that Council member now.

### 5. Graphify consistency

```bash
py -3 -m graphify update .claude/notes/
```
Run after any `.claude/notes/` write. If AMBIGUOUS edges appeared on concepts this task touched, `knowledge_validator` must resolve them before ship.

### 6. Karpathy invariant

```bash
find .claude/memory -name '*.md' 2>/dev/null
```
Empty. Non-negotiable.

### 7. Observability trace

`.claude/observability/traces.json` contains at least one record with:
- `task_id` matching this task.
- `agent_chain` listing the agents invoked.
- `verdict` field populated.

No trace → work bypassed the canonical loop → task not done.

### 8. Git status intentional

```bash
git status --short
```
Every listed file is EITHER:
- Staged for the current commit (intended), OR
- Explicitly ignored / unrelated (state this fact).

Nothing "I don't know where this came from". Investigate any unknown file.

## Report format

Compact, grep-able, one line per check:

```
[1/8] tests      PASS  44/44 in 8.2s
[2/8] audit      PASS  10.0/10 PASS
[3/8] spec       PASS  AC1-AC5 satisfied (trace: t-abc123)
[4/8] council    PASS  critic=MEDIUM eval=pass sec=skip kv=pass refl=captured
[5/8] graphify   PASS  0 new AMBIGUOUS edges on <concept-list>
[6/8] karpathy   PASS  memory/ clean
[7/8] trace      PASS  task_id=t-abc123 at 2026-04-24T15:42Z
[8/8] git        PASS  3 files staged, working tree otherwise clean
```

Failure example:
```
[4/8] council    FAIL
       critic flagged 1 CRITICAL (cardinality DoS, see case-study/.../COUNCIL_VERDICT.md)
       Next: loop back to worker with findings; re-run this skill after fix
```

## Red flags to refuse

| Thought | Reality |
|---|---|
| "Tests mostly pass, good enough" | 43/44 is NOT 44/44. Fix the failing one or revert. |
| "Audit dropped 1 point but still passing" | Silent regression. Diagnose what got worse. |
| "SPEC AC is minor, fine to skip" | Re-convene Planning Council. Don't unilaterally descope. |
| "Council didn't review, I'll add the note later" | Now is later. Dispatch critic+evaluator now. |
| "Graphify can be refreshed after the PR merges" | Unresolved AMBIGUOUS edges mean a future reader will be misled. Resolve now. |

## After pass

Proceed to `/commit` (which runs `pre-commit-checklist` skill) or `/commit-push-pr`. Tell the user: "Verified. 8/8 gates passed. Ready to ship."

## Order vs pre-commit-checklist

```
                 you say "done"
                       │
                       ▼
               verification-before-ship  (this skill — 8 gates)
                       │
                       ▼
                    /commit
                       │
                       ▼
               pre-commit-checklist  (7 gates; overlap but commit-focused)
                       │
                       ▼
                   actual commit
```

Both skills run. The overlap (tests, harness, karpathy, trace) is intentional — two independent runs catch eventual-consistency bugs in the tooling itself.

## When to skip

Never. Even for hotfixes, run a reduced version (gates 1, 6, 7, 8 at minimum) and log the rationale.
