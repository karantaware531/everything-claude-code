# /nightly-review

Manually trigger the Council-authorized nightly improvement routine.

Default schedule is daily 16:03 local time (via Claude Code CronCreate). This
command runs it on demand.

## What it does

1. Fetches the 10 canonical Claude Code docs (code.claude.com/docs/en/*).
2. Diffs content hashes against the previous run (cached in `memory/nightly_doc_hashes.json`).
3. For any changed doc, generates a proposal at `.claude/notes/concepts/proposals/nightly-<date>.md`.
4. Submits proposal to Consensus Council via protocol envelope (traces in `observability/traces.json`).
5. Auto-applies tier 1-2 changes; surfaces tier 3+ to user for next-session review.
6. Triggers graphify `--update` to index the proposal.
7. Logs run to `memory/logs.json` with `outcome: nightly_improvement_run`.

## Usage

```bash
/nightly-review               # full run (fetch + diff + propose + Council + log)
```

Behind the scenes:
```bash
py -3 .claude/tools/nightly_improvement.py
```

## Dry run (preview without writing)

```bash
py -3 .claude/tools/nightly_improvement.py --dry-run
```

## Disable

```bash
export AGENTIC_OS_NIGHTLY_DISABLED=1   # kill switch
```

## Behavior per council verdict

| Verdict | Action |
|---|---|
| `no_op` | No doc changes detected; log-only exit |
| `await_next_session` | Proposal written; Council will deliberate on next interactive session |
| (future) `auto_apply` | Tier 1-2 changes applied immediately + logged |
| (future) `escalate` | Tier 3+ changes blocked pending user approval |

## Where proposals live

- `.claude/notes/concepts/proposals/nightly-<YYYY-MM-DD>.md`
- Indexed by Graphify on next `--update`; queryable via `/graphify-query "nightly proposals"`.

## Observability

- Traces: `.claude/observability/traces.json` (one envelope per Council member per run)
- Log: `.claude/memory/logs.json` (one `nightly_improvement_run` entry per run)
- Cache: `.claude/memory/nightly_doc_hashes.json` (previous-run hashes for diff)
