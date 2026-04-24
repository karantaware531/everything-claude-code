---
name: pre-commit-checklist
description: Use BEFORE every `/commit` or `git commit`. Runs the 7-point pre-commit gate — test_runner 44/44, harness_audit ≥ 8, no secrets in diff, no .md in memory/, SPEC compliance (if Planning Council used), policy_guard clean, observability trace recorded. Refuses to commit if any gate fails.
license: MIT
compatibility: Agentic OS v5.7+ (requires test_runner.py and harness_audit.py)
metadata:
  project: agentic-os
  version: "5.7"
  trigger: "/commit, git commit, ready to commit"
  mandatory_before: "commit"
  rigid: "true"
---

# Pre-commit checklist — the 7-point gate

**Rigid skill. Run every check in order. Do not skip.** Failing any check → block commit, surface failure, do not try to work around.

## Why rigid

Commits are shipped artifacts. Ship Council retains full veto on commit quality. This skill enforces the minimum gate before `/commit` or raw `git commit`. Skipping it means Ship Council catches issues post-hoc at ~80k tokens per loop-back. Catching here costs ~3 minutes.

## Checklist (in order)

### 1. Test runner — 44/44 green

```bash
py -3 .claude/tools/test_runner.py
```

Must report `44/44 checks passed`. Any failure → STOP. Investigate the failing check first. Never comment out or skip a failing check.

### 2. Harness audit — ≥ 8.0 overall

```bash
py -3 .claude/tools/harness_audit.py
```

Must report overall ≥ 8.0 and verdict `PASS`. Check per-category scores if degraded — some categories regressing silently is a v5.7 red flag.

### 3. Diff secret scan

```bash
git diff --cached | grep -iE "(api[_-]?key|password|secret|token|private[_-]?key|bearer|aws_[a-z_]+_key)" | head
```

ANY hit → STOP. Inspect. If a genuine secret landed, remove from staging AND rotate the secret (scrubbing history is insufficient). If false positive (documentation pattern), justify in commit message.

### 4. Karpathy invariant

```bash
find .claude/memory -name '*.md' 2>/dev/null
```

Must be empty. Any `.md` in memory/ → revert, re-route to `.claude/notes/`. This is non-negotiable (see values.yaml).

### 5. SPEC compliance (if Planning Council was convened)

If `.claude/notes/planning-council/<current-task-slug>/SPEC.md` exists for this task:
- Read SPEC §7 (acceptance criteria).
- For each AC, verify the commit satisfies it.
- If any AC is unsatisfied AND you're committing anyway, the commit must be labeled `PARTIAL:` and log a `planning-council-deviation` entry to `memory/logs.json`.
- If an AC was deliberately descoped mid-execution, re-convene Planning Council (not inline fix).

If no SPEC exists (opt-out path was used), skip this check.

### 6. policy_guard dry-run on staged writes

```bash
git diff --cached --name-only | while read -r f; do
  py -3 .claude/tools/policy_guard.py --action "write:$f" || echo "DENIED: $f"
done
```

Any `DENIED` → STOP. Either the file is in security.yaml denylist (don't commit), or the allowlist needs a legitimate amendment (tier-4 via `policy_amendment` log).

### 7. Trace recorded

`.claude/observability/traces.json` must have at least one append with today's date AND the current task_id. If empty / stale, the work bypassed the canonical loop — surface this and ask whether Ship Council review happened.

## Report format

Emit one line per check. Pass = one short line. Fail = 3 lines (check name, failure reason, suggested next step).

```
[1/7] tests    PASS  44/44
[2/7] audit    PASS  10.0/10
[3/7] secrets  PASS  no patterns matched
[4/7] karpathy PASS  memory/ clean
[5/7] spec     PASS  AC1-AC4 satisfied
[6/7] policy   PASS  9 staged files allowlist-clean
[7/7] trace    PASS  task_id=t-abc123 at 2026-04-24T15:42Z
```

On failure, format:
```
[3/7] secrets  FAIL
       .env-like pattern in src/config.py:42
       Next: remove line, rotate secret, re-stage
```

## Red flags / rationalizations to refuse

| Thought | Reality |
|---|---|
| "Tests are flaky, just rerun" | Rule: no flaky tests. Root-cause or revert. |
| "Secret is placeholder, safe to commit" | Placeholders match real-secret patterns in scanners. Remove before commit. |
| "SPEC deviation is minor, fine" | Minor deviation becomes scope creep. Re-convene Planning Council. |
| "policy_guard denies because allowlist is stale" | Stale allowlist = tier-4 policy_amendment with rationale. Don't `--force`. |

## After pass

Hand off to `/commit` or `/commit-push-pr`. Those skills assume this gate already passed.

## Failure recovery

If this skill itself fails unexpectedly (hook crash, tool not found, etc.):
1. Do NOT commit.
2. Check `AGENTIC_OS_HOOKS_DISABLED` — if set, unset first.
3. Run each check manually to isolate the failing step.
4. If `test_runner.py` itself is broken, escalate to user (tier 3+).
