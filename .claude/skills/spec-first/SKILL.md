---
name: spec-first
description: Use BEFORE writing any production code. Writes a contract spec (public API, invariants, acceptance criteria, failure modes) and gets it reviewed by critic + evaluator BEFORE implementation begins. Distinct from TDD — adds Council sign-off on the contract before the first test is written.
license: MIT
compatibility: Agentic OS v5.7+ (uses critic + evaluator agents from governance layer)
metadata:
  project: agentic-os
  version: "5.7"
  trigger: "implement X, add feature, build new, after /lead-agent SPEC phase"
  rigid: "true"
  complements: "superpowers:test-driven-development"
---

# Spec-first — contract before code

Write the **contract** before the implementation. Contract = public API + invariants + acceptance criteria + explicit failure modes. This skill gets the contract red-teamed by Council (critic + evaluator) BEFORE you write a single test or line of code.

**Complements — does not replace — TDD** (`superpowers:test-driven-development`). Order:
```
spec-first → critic+evaluator sign-off → TDD writes failing test → code → verification-before-ship
```

If `/lead-agent` already ran, SPEC.md from Planning Council supersedes this skill for the overall task. Use spec-first for sub-features within an approved SPEC.

## Why rigid

Flaws in the contract propagate through every downstream artifact — tests, docs, callers. Fixing a contract post-implementation is expensive (breaks callers, invalidates tests). Catching contract flaws at the spec stage is the cheapest moment.

## The contract (minimum fields)

Write to `specs/<feature-slug>.md` in the target module, or inline in the PR description if small. Required sections:

### 1. Purpose
One sentence. What capability does this add, for whom?

### 2. Public surface
- Functions / classes / endpoints / CLI flags.
- EXACT signatures. Types. Default values.
- What's internal and NOT part of the contract.

### 3. Invariants
- Pre-conditions (what the caller guarantees).
- Post-conditions (what this code guarantees).
- Thread-safety / concurrency expectations.
- Idempotency guarantees.

### 4. Acceptance criteria
- AC1: Given X, when Y, then Z.
- AC2: …
- Each AC must be testable (no "should feel fast" — use "p99 < 50ms at 10k RPS").

### 5. Failure modes
- What inputs cause what failures?
- What external failures are handled? Ignored? Escalated?
- What's the retry / timeout / circuit-break policy?

### 6. Non-goals
- Explicit scope limits. "This does NOT handle streaming" etc.
- Why they're out of scope.

### 7. Open questions
- Ambiguities you want Council to resolve.

## Procedure

### Step 1 — Draft the spec

Write the 7 sections. Avoid describing implementation. If you catch yourself writing "use a hashmap" in §2, rewrite as "O(1) lookup" — that's the contract, hashmap is implementation.

### Step 2 — Invoke critic + evaluator on the spec

Fan-out in parallel via Task tool:

```
critic:
  Review this spec: <content>.
  Red-team it. Flaws, missing cases, ambiguity, hidden coupling.
  Severity: CRITICAL | HIGH | MEDIUM | LOW.

evaluator:
  Grade this spec for completeness against §Acceptance criteria.
  Missing ACs? Untestable ACs? Circular definitions?
  Pass / fail with score.
```

### Step 3 — Iterate

For each CRITICAL or HIGH from critic, revise the spec. For each evaluator `fail`, revise. Loop back to step 2.

Max 2 iterations before escalating to user (tier 3) — if the contract can't converge in 2 rounds, the feature is likely ambiguous and needs scope split, not more spec rounds.

### Step 4 — Sign-off

Spec approved when critic returns ≤ MEDIUM AND evaluator returns pass. Mark the spec file:

```yaml
---
status: approved
approved_by: [critic, evaluator]
approved_at: <ISO-8601>
---
```

### Step 5 — Hand to TDD

Now — and only now — write the failing test. Use `superpowers:test-driven-development` from this point.

## Relation to /lead-agent Planning Council

| Stage | What's covered |
|---|---|
| `/lead-agent` SPEC.md | Overall feature / task scope, specialist roster, task-level ACs |
| `spec-first` sub-feature spec | Internal module contract, public surface, per-function invariants |

Planning Council SPEC is task-level. spec-first is module-level. Both can coexist; the module spec must not contradict the Planning Council SPEC.

## Red flags to refuse

| Thought | Reality |
|---|---|
| "Spec is obvious, skip to code" | Obvious specs take 10 min to write and save hours of rework. Write it. |
| "TDD covers this already" | TDD catches IMPLEMENTATION flaws. Spec-first catches CONTRACT flaws. Different layer. |
| "The spec is the code" | Code describes how. Contract describes what. Future callers read the contract. |
| "Critic will flag nothing on a small change" | Small changes with bad contracts become big refactors. Run critic anyway. |

## Output

- Spec file (7 sections, frontmatter).
- critic verdict + evaluator verdict persisted to `.claude/observability/traces.json`.
- Hand-off tag: `spec-first: approved for <feature-slug>`.

## When to skip

- Pure bug fix (no new contract). Use `superpowers:systematic-debugging` instead.
- Trivial rename / refactor (no contract change).
- Single-line hotfix.
- Research / exploratory reading (no code output).
