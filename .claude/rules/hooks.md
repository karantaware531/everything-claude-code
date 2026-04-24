---
paths:
  - ".claude/hooks/**/*.py"
---

# Hook Script Contract

## Exit codes
- `0` — allow; stdout injected into Claude context (SessionStart, UserPromptSubmit, UserPromptExpansion only)
- `2` — block (PreToolUse only); stderr sent to Claude as feedback
- Any other — allow; first stderr line shown as hook error notice

## Structured JSON output (preferred over exit codes for complex decisions)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask|defer",
    "permissionDecisionReason": "<string>"
  },
  "additionalContext": "<string injected into Claude>",
  "decision": "block"
}
```

## Input
Read JSON event from stdin:
```python
import json, sys
event = json.loads(sys.stdin.read())
tool_name = event.get("tool_name")
tool_input = event.get("tool_input", {})
```

## Conventions
- Python 3.10+ stdlib only (matches project constitution).
- Must respect `AGENTIC_OS_HOOKS_DISABLED=1` — early-return `exit(0)` when set.
- Keep execution under 100ms for PreToolUse hooks (every tool call pays this cost).
- Use stderr for block reasons (shown to user/Claude); stdout for context injection.
- Never block Stop, SessionEnd, or lifecycle-cleanup events — log and continue.
- Import only `json`, `sys`, `os`, `pathlib`, `subprocess`, `datetime`. Avoid network/heavy deps.

## Registration
Every hook must be:
1. Declared in `.claude/settings.json` under the correct event key.
2. Listed in `.claude/tools/tool_registry.json` with `hook:<name>` prefix.
3. Verified by `test_runner.py` (it AST-parses every registered hook).

## Path convention (v5.5.1 — MANDATORY)

**Every hook command MUST use `$CLAUDE_PROJECT_DIR` for the script path.** Relative
paths break when CWD drifts outside repo root during a session (e.g. after
`cd subfolder`), triggering a self-inflicted lockout where every tool call fails
because the hook can't find its own script.

✅ Correct:
```json
{"command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/my_hook.py\""}
```

❌ Wrong (forbidden):
```json
{"command": "python .claude/hooks/my_hook.py"}
```

Regression guard: `test_runner.py` check #42 fails any hook command missing
`$CLAUDE_PROJECT_DIR`. Source incident: `memory/logs.json` entry
`v5.5.1-hook-path-cwd-fix` (2026-04-24).
