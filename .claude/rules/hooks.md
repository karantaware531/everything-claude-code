---
paths:
  - ".claude/hooks/**/*.py"
---

# Hook Script Contract

## Exit codes
- `0` — allow; stdout injected into Claude context (SessionStart, UserPromptSubmit, UserPromptExpansion only)
- `2` — block (PreToolUse, PermissionRequest, UserPromptSubmit, UserPromptExpansion, Stop, PreCompact); stderr sent to Claude as feedback
- Any other — allow; first stderr line shown as hook error notice

## Structured JSON output (preferred over exit codes for complex decisions)
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask|defer",
    "permissionDecisionReason": "<string>",
    "updatedInput": {},
    "additionalContext": "<string injected into Claude>"
  },
  "decision": "block",
  "systemMessage": "<warning shown to user>"
}
```

### updatedInput — modify tool input in-flight (PreToolUse)
Return `hookSpecificOutput.updatedInput` to rewrite the tool's arguments before execution.
Example: canonicalize a file path before Write executes.

### additionalContext — inject context into Claude's view (any event)
Return `hookSpecificOutput.additionalContext` to add structured context visible to Claude.
Example: SessionStart hook injecting git branch name, active issues.

### permissionDecision: "defer" (v2.1.89+ — non-interactive mode only)
Defer the permission decision to an external handler. Only works for single tool calls in non-interactive (`-p`) mode.

## All supported hook lifecycle events

### Session-level
- `SessionStart(startup|resume|clear|compact)` — session begins/resumes
- `SessionEnd(clear|logout|other)` — session terminates
- `Setup(init|maintenance)` — during --init-only or -p with --init

### Turn-level
- `UserPromptSubmit` — before Claude processes user prompt (blockable via exit 2)
- `UserPromptExpansion` — when slash command expands (blockable via exit 2)
- `Stop` — when Claude finishes responding (blockable to force continuation)
- `StopFailure` — when turn ends due to API error

### Agentic loop (per tool call)
- `PreToolUse(ToolName)` — before tool executes (blockable)
- `PermissionRequest` — when permission dialog appears (blockable)
- `PermissionDenied` — when auto-mode classifier denies tool
- `PostToolUse(ToolName)` — after tool succeeds
- `PostToolUseFailure` — after tool fails
- `PostToolBatch` — after batch of parallel tools resolves

### Lifecycle/config
- `InstructionsLoaded` — CLAUDE.md or rules/*.md loaded (debug: log which file and why)
- `ConfigChange` — configuration file changed
- `CwdChanged` — working directory changed
- `FileChanged` — watched file changed
- `WorktreeCreate / WorktreeRemove` — git worktree lifecycle
- `PreCompact / PostCompact` — context compaction (PreCompact blockable)
- `SubagentStart / SubagentStop` — subagent lifecycle
- `TaskCreated / TaskCompleted` — agent team task management
- `TeammateIdle` — agent team teammate going idle
- `Notification(permission_prompt|auth_success)` — Claude sends notification
- `Elicitation / ElicitationResult` — MCP user input

## Handler types (5 types)

### 1. command (existing)
```json
{"type": "command", "command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/my.py\"", "async": false, "asyncRewake": false}
```

### 2. http (new)
```json
{"type": "http", "url": "http://localhost:8080/hooks", "headers": {"Authorization": "Bearer $TOKEN"}, "allowedEnvVars": ["TOKEN"], "timeout": 30}
```
POST JSON body (same format as stdin). 2xx + JSON = success. Non-2xx = non-blocking error.

### 3. mcp_tool (new)
```json
{"type": "mcp_tool", "server": "my_server", "tool": "validate", "input": {"file": "${tool_input.file_path}"}}
```
Calls a tool on a connected MCP server. Useful for delegating validation to specialized MCP services.

### 4. prompt (new)
```json
{"type": "prompt", "prompt": "Is this safe? $ARGUMENTS", "model": "fast", "timeout": 30}
```
Single-turn Claude evaluation. Fast model (Haiku) default. Good for semantic classification that shell scripts can't do.

### 5. agent (new — experimental)
```json
{"type": "agent", "prompt": "Validate: $ARGUMENTS", "timeout": 60}
```
Runs a subagent with tool access for complex validation. Use sparingly (latency cost).

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
