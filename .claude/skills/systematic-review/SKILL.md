---
name: systematic-review
description: Our structured code review protocol. Reads diff, git blame on touched lines, downstream callers, test coverage delta, and runs security-pattern scan against the diff. Produces a critic-shaped report. Use for /review and before any major-change commit. Complements the built-in `/review` command and plugin `review` skill by adding our trust-matrix signal and Graphify-aware cross-call impact.
license: MIT
compatibility: Agentic OS v5.7+ (uses Ship Council + trust_matrix + security_reminder_hook)
metadata:
  project: agentic-os
  version: "5.7"
  trigger: "/review, review this change, before /commit-push-pr on > 5 file diff"
  rigid: "true"
  complements: "voltagent-qa-sec:code-reviewer, engineering:code-review"
---

# Systematic review — 6-lens code review

Single-pass review is lossy. Rotate through 6 lenses; write findings as one structured report; hand to Ship Council.

## Why rigid

Reviews that say "looks good" or "nitpicks only" usually miss structural issues (downstream call breakage, test gap, security regression). Rotating lenses catches what a single read doesn't. Each lens has a specific question; stay on the question.

## Preconditions

- Diff is available (staged changes, branch ahead of main, or a PR URL).
- You can read the repo (Glob/Grep/Read).
- Trust matrix (`.claude/memory/trust_matrix.json`) exists if available (non-blocking).

## The 6 lenses (run in order)

### Lens 1 — Diff scan (3 min)

```bash
git diff --stat <base>..HEAD     # file-level overview
git diff <base>..HEAD            # actual content
```

Note:
- Files touched (count + paths).
- Net lines added vs removed.
- Deletions that LOOK like deletions of tests or docs — flag.
- Binary / large files (>1k lines) — flag.

### Lens 2 — Authorship / blame (2 min)

For each non-trivial block changed:

```bash
git blame <base>..HEAD -- <file>
```

Ask:
- Is this code being rewritten wholesale by someone who didn't originally author it?
- Is there a comment left by the original author warning against this change?
- Is this touching a "do not touch" file (protected paths per `policy_guard`)?

### Lens 3 — Downstream callers (3 min)

For each exported symbol touched (function, class, type, CLI flag, API endpoint):

```bash
grep -rn "<symbol_name>" --include="*.py" --include="*.ts" <repo_root>
```

Or use Graphify:
```
/graphify-query "callers of <symbol>"
```

Ask:
- Do the callers assume a contract the diff broke? Signature drift? Return-type change?
- Are there tests on the caller side that will now fail?
- If this is an API/CLI, is there a migration note in the commit message?

### Lens 4 — Test coverage delta (2 min)

```bash
git diff <base>..HEAD -- "*test*" "*spec*"
```

Ask:
- Was a test added for the new behavior? (If feature) mandatory.
- Was a test modified to pass the new behavior? Explain why the OLD test was wrong.
- Was a test DELETED? (Huge red flag — `testing.md` rule: never delete failing tests to make suite green.)
- If this is a bug fix, is there a reproducer test?

### Lens 5 — Security pattern scan (2 min)

Run the diff through the dangerous-pattern list defined in
`.claude/rules/security-patterns.md` and enforced at hook-time by
`.claude/hooks/security_reminder_hook.py` (see the SECURITY_PATTERNS list there
for the canonical set — dynamic code eval, unsafe HTML sinks, shell-injection
classes, unsafe deserialization, unsafe child-process wrappers, GitHub Actions
expression injection).

```bash
# pipe the diff through the project's security-pattern scanner
git diff <base>..HEAD > /tmp/diff.txt
py -3 .claude/hooks/security_reminder_hook.py < /tmp/diff.txt || true
```

Any hit: the hook either ALREADY blocked this OR was bypassed. Investigate.
Legitimate uses need justification comment + `/review` sign-off.

Also manually check:
- New `.env` / credential-looking strings in diff.
- New shell commands with unquoted variables.
- New `.github/workflows/*.yml` with `${{ github.event.* }}` used inside `run:` blocks.

### Lens 6 — Our observability + trust matrix (3 min)

```bash
cat .claude/memory/agent_history.json | tail -50 | grep <current_agent_id>
cat .claude/memory/trust_matrix.json 2>/dev/null
```

Ask:
- Has the producing agent been failing lately? (Recent failure rate > 0.2 → extra scrutiny.)
- Were the upstream agents in this task chain ones we trust?
- Is the change part of a longer DAG where earlier nodes failed and this is a retry? (Check `observability/traces.json` for task_id.)

## Report format — critic-shaped

Single structured report:

```markdown
## Review: <task-slug or PR #>

### Summary
<1-2 sentences: what changed, overall assessment>

### Findings

- [CRITICAL] <issue> — evidence: <file:line> — fix: <suggestion>
- [HIGH]     <issue> — evidence: <file:line> — fix: <suggestion>
- [MEDIUM]   <issue> — evidence: <file:line>
- [LOW]      <issue> — evidence: <file:line>

### Coverage
- Tests added: <count>
- Tests modified: <count>
- Tests deleted: <count>  <!-- must be 0 unless justified -->

### Downstream impact
- Callers checked: <count>
- Breakages: <list or "none">

### Security scan
- Patterns matched: <list or "none">
- New sensitive surface: <list or "none">

### Trust signal
- Producing agent recent failure rate: <float>
- Upstream trust: <score or "n/a">

### Verdict
- [ ] SHIP
- [ ] LOOP-BACK (findings above)
- [ ] ESCALATE (tier ≥ 3)
```

## Handoff to Ship Council

After report, invoke Ship Council (critic + evaluator + security if sensitive + knowledge_validator if graph touched):

```
critic.review(diff, findings=this_report)
evaluator.grade(diff, spec=<SPEC if Planning Council ran>)
security.assess(diff)             # if sensitive
knowledge_validator.resolve(edges) # if AMBIGUOUS on graph
```

Their verdicts go into `observability/traces.json`.

## Red flags to refuse

| Thought | Reality |
|---|---|
| "Diff is tiny, skip lenses 3-6" | Tiny diffs to core modules have broken systems. Run all 6. |
| "I wrote this, I know it's good" | Self-review misses the most. Lens 2 (blame) exists for this. |
| "Tests were out of date, I fixed them by removing" | testing.md: never delete failing tests. Revert. |
| "Trust matrix is noisy, ignore" | Even noisy signal is signal. Note + proceed; don't skip. |

## When to skip

Never skip outright. For trivial changes (one-line typo fix, doc-only change), reduce to lenses 1 + 4 + 5. Full 6 lenses for anything touching `.claude/core/`, `.claude/agents/`, `.claude/policies/`, or any public API.
