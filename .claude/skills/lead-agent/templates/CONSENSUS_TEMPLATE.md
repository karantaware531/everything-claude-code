---
type: consensus
task: <task-slug>
spec_ref: SPEC.md
assignments_ref: TASK_ASSIGNMENTS.md
result: APPROVED | APPROVED_WITH_RESERVATIONS | BLOCKED
rounds: 1 | 2 | 3
escalated: false | true
---

# CONSENSUS — <Task Title>

## Round <N>

### Tally
| Role | Verdict | Notes |
|---|---|---|
| architecture | APPROVE | — |
| performance | APPROVE_WITH_RESERVATION | "p99 target tight; may need cache later" |
| security | APPROVE | — |
| qa | APPROVE | — |
| data | APPROVE | — |
| design | APPROVE | — |
| product | APPROVE | — |
| development | APPROVE | — |
| docs | APPROVE | — |

### Blocks (if any)
- B1 by <role>: <specific objection>
  - Resolution: <what was changed in SPEC.md to resolve> (or `unresolved → re-debate`)

### Reservations carried into execution
- Rv1 (<role>): … — Ship Council will pay attention here.

## Ship Council SPEC pre-review

- critic verdict: <severity>, <one-line summary>
- evaluator verdict: <pass | fail>, <coverage%>

## Final decision
<APPROVED / APPROVED_WITH_RESERVATIONS / BLOCKED → <next action>>

## Signatures (role: agent_id)
- architecture: <agent_id>
- performance: <agent_id>
- security: <agent_id>
- qa: <agent_id>
- data: <agent_id>
- design: <agent_id>
- product: <agent_id>
- development: <agent_id>
- docs: <agent_id>

## Handoff
Approved SPEC + TASK_ASSIGNMENTS are BINDING on all downstream executors.
Deviation requires re-convening the Planning Council.
