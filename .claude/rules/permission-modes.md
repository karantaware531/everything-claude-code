# Permission Modes — Cheatsheet (always-on rule)

> Agentic OS default: **`acceptEdits`** (v5.5).
> Rationale: Consensus Council (critic + evaluator + security + reflection + knowledge_validator)
> plus 6 safety layers (security.yaml, policy_guard hook, gateguard hook, security_reminder hook,
> values.yaml, council veto) replace per-edit approval friction.

## The 6 permission modes

| Mode | What it does | When to use it |
|---|---|---|
| `default` | Ask for approval on every write, shell, network action | First-time exploration in an unfamiliar repo; when you do not yet trust the Council |
| **`acceptEdits`** (ours) | Writes + edits + common-fs Bash pass without prompt. Other tools still prompt. | Normal coding sessions, refactors, doc writes. **Our default.** |
| `plan` | Read-only exploration. Write proposals only, no actual writes. | Risky refactors before committing; understanding a new codebase; security audit |
| `auto` (v2.1.83+) | All actions gated by background classifier (Sonnet 4.6 / Opus 4.6+) | Highly active coding when you want full autonomy + classifier-level safety |
| `dontAsk` | Only pre-approved tools (`permissions.allow` list) run; deny everything else | **CI pipelines** via `claude -p`. Never interactive. |
| `bypassPermissions` | Skips ALL permission checks except protected paths | Emergencies. Log as `constitution_amendment`. Audit after. |

## Switching modes in a session

```bash
/permissions  # interactive UI to change mode
```

Or via CLI flag:
```bash
claude --permission-mode plan      # enter plan mode
claude --permission-mode dontAsk   # CI batch mode
```

Or in `settings.json`:
```json
{"permissions": {"defaultMode": "acceptEdits"}}
```

## Per-task-type recommendations

| Task type | Recommended mode | Why |
|---|---|---|
| Feature coding | `acceptEdits` | Council + hooks catch issues; friction-free flow |
| Bug fix | `acceptEdits` | Same; `/debug` command enforces evidence-first |
| Refactor (wide diff) | `plan` → `acceptEdits` | Plan first to understand blast radius, then execute |
| Risky DB migration | `plan` → user-reviewed → `acceptEdits` | High-stakes; plan exposes approach before action |
| Security audit | `plan` | Read-only by intent; proposal artifacts only |
| Research / reading | `default` or `plan` | Minimal write intent |
| Doc writes | `acceptEdits` | Low risk; Council catches factual errors |
| CI / batch scripts | `dontAsk` | No human available; allowlist scoped |
| Constitution / policy edits | `default` → tier 4 → user approval | Always user-gated |
| Emergency hotfix | `bypassPermissions` → log → `acceptEdits` | Fast unblock; audit within 24h |

## Protected paths — never auto-approved in ANY mode

Even `bypassPermissions` cannot touch these without explicit user gesture:

```
.git/           .vscode/        .idea/          .husky/
.claude/        (except commands/, agents/, skills/, worktrees/)
.gitconfig      .gitmodules     .bashrc         .bash_profile
.zshrc          .zprofile       .profile        .ripgreprc
.mcp.json       .claude.json
```

## Our Consensus-Council safety net (why `acceptEdits` is safe here)

Before ANY output ships to user/production:

```
Worker produces edit
    │
    ▼
gateguard hook         ← protected-path block or fact-forcing
security_reminder hook ← 9 content vuln patterns blocked
policy_guard hook      ← allow/deny yaml enforcement
    │
    ▼ (all hooks pass)
critic                 ← red-teams; flags CRITICAL/HIGH/MEDIUM/LOW
evaluator              ← grades correctness + completeness
security               ← (if sensitive) novel threat analysis
knowledge_validator    ← (if AMBIGUOUS edges touched) resolve
reflection             ← captures strategy/experience
    │
    ▼ (council unanimous or user approves any veto)
SHIP
```

Any hook block → exit 2 → tool call fails regardless of permission mode.
Any council veto → orchestrator escalates to user (tier 3+).

## Auditing mode changes

`ConfigChange` hook (in `settings.json`) logs every permission mode change to
`memory/logs.json`. Audit trail: `cat .claude/memory/logs.json | jq '.entries[] | select(.outcome=="config_change")'`.

## Disable hooks entirely

Global kill switch for tier-4 amendments:
```bash
export AGENTIC_OS_HOOKS_DISABLED=1
```

Use sparingly. Log the bypass as `policy_amendment` in `memory/logs.json`.
