---
type: spec
task: <task-slug>
status: approved | draft | blocked
approved_by: [list of specialist roles]
version: 1
supersedes: <prior-spec-slug or null>
---

# SPEC — <Task Title>

## 1. Summary
<2-3 sentences: what we're building and why>

## 2. Goals
- G1: <measurable outcome>
- G2: …

## 3. Non-goals
- NG1: <explicit scope limit>
- NG2: …

## 4. Stakeholders & users
- Primary users: <who>
- Secondary users: <who>
- Operators / oncall: <who>

## 5. Constraints (from perspectives)

### 5a. Architecture (MUST)
- …

### 5b. Performance (MUST)
- Latency budget: p50=<x>ms, p99=<y>ms
- Throughput: <N>/sec sustained
- Memory: <M> MB per instance

### 5c. Security (MUST)
- Threat model summary: <link to perspectives/security.md>
- Data classification: <public | internal | sensitive | secret>
- Authz model: <RBAC | ABAC | none>

### 5d. Quality (MUST)
- Test coverage target: <N>%
- Required test types: [unit, integration, e2e, perf, fuzz]
- Flakiness tolerance: 0

### 5e. Data (MUST)
- Schema: <summary>
- Migrations: <forward-only | reversible>
- Retention: <duration>

### 5f. Design / UX (if applicable)
- Accessibility: WCAG 2.1 <AA | AAA>
- Key flows: <summary>

### 5g. Product (if applicable)
- Success metric: <primary KPI>
- MVP scope: <what ships day 1>

## 6. Public contracts
<APIs, CLI flags, DB schemas, event shapes — exact definitions>

## 7. Acceptance criteria
- AC1: Given X, when Y, then Z
- AC2: …

## 8. Verification plan
- Unit: <which modules>
- Integration: <which seams>
- Perf: <bench target>
- Security: <audit scope>

## 9. Open risks (carried forward)
| # | Risk | Severity | Mitigation | Owner |
|---|---|---|---|---|
| R1 | … | high/med/low | … | <role> |

## 10. Rollout
- Phase 1: …
- Phase 2: …
- Rollback: <how>

## 11. Out of scope (with rationale)
- Item: reason for deferral

## 12. References
- perspectives/*.md
- DEBATE.md
- CONSENSUS.md
- TASK_ASSIGNMENTS.md
