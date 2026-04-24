---
domain: concepts
slug: claude-code-best-practices-v5.4
source: https://code.claude.com/docs/en/
first_observed: 2026-04-24T00:00:00Z
last_updated: 2026-04-24T00:00:00Z
confidence: 1.0
task_id: v5.4-anthropic-doc-ingest
---

# Claude Code Canonical Best Practices (Anthropic docs, 2026-04-24)

Synthesis of 10 official pages: overview, features, .claude-directory, context-window,
memory, permission-modes, best-practices, sub-agents, agent-teams, hooks-guide.

## Canonical feature inventory

### Extension layers
- `CLAUDE.md` (project) + `CLAUDE.local.md` (personal, gitignored) + managed (OS-level MDM)
- Auto `MEMORY.md` — `~/.claude/projects/<proj>/memory/` (v2.1.59+; 200 lines or 25KB loaded)
- `.claude/skills/<n>/SKILL.md` — replaces `.claude/commands/` for new workflows
- `.claude/commands/` — legacy (fully supported; skills take precedence on name conflict)
- `.claude/rules/<n>.md` — path-scoped rules with `paths:` YAML frontmatter
- `.claude/agents/<n>.md` — custom subagents
- `.claude/hooks/` — lifecycle scripts
- `.claude/agent-memory/<agent>/` — project-scoped agent persistent memory
- `.claude/agent-memory-local/` — gitignored agent memory
- `.mcp.json` at repo root — project MCP servers
- `.worktreeinclude` at repo root — gitignored files to copy to new worktrees

### All 28 hook events
`SessionStart`, `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PermissionRequest`,
`PermissionDenied`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`, `Notification`,
`SubagentStart`, `SubagentStop`, `TaskCreated`, `TaskCompleted`, `Stop`, `StopFailure`,
`TeammateIdle`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `FileChanged`,
`WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`, `Elicitation`,
`ElicitationResult`, `SessionEnd`.

### Hook types: `command`, `http`, `mcp_tool`, `prompt`, `agent`

### Hook exit-code semantics
- 0 → allow; stdout injected into Claude context (SessionStart/UserPromptSubmit/UserPromptExpansion)
- 2 → block; stderr sent to Claude as feedback
- Any other → allow; first stderr line shown as error notice
- JSON stdout + exit 0 → structured control: `{hookSpecificOutput: {permissionDecision: allow|deny|ask|defer, ...}, additionalContext: "..."}`

### 6 permission modes
`default`, `acceptEdits`, `plan`, `auto` (v2.1.83+), `dontAsk`, `bypassPermissions`

### Subagent frontmatter fields
`name`, `description`, `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`,
`skills`, `mcpServers`, `hooks`, `memory` (user|project|local), `background`, `effort`,
`isolation` (worktree), `color`, `initialPrompt`

### Skill frontmatter fields
`name`, `description`, `disable-model-invocation`, `user-invocable`, `argument-hint`, `context`

### Context window load order at session start
1. System prompt (~4200t)
2. Auto memory / MEMORY.md (~680t)
3. Environment info (~280t)
4. MCP tool names deferred (~120t)
5. Skill descriptions (~450t; `disable-model-invocation: true` skips)
6. `~/.claude/CLAUDE.md` (~320t)
7. Project `CLAUDE.md` (~1800t)

### Protected paths (never auto-approved in any mode)
`.git`, `.vscode`, `.idea`, `.husky`, `.claude` (except commands/agents/skills/worktrees subdirs),
`.gitconfig`, `.gitmodules`, `.bashrc`, `.bash_profile`, `.zshrc`, `.zprofile`, `.profile`,
`.ripgreprc`, `.mcp.json`, `.claude.json`.

### Settings.json canonical keys
`permissions.allow`, `permissions.deny`, `permissions.defaultMode`, `hooks`, `statusLine`,
`model`, `env`, `outputStyle`, `autoMemoryEnabled`, `autoMemoryDirectory`, `claudeMdExcludes`,
`sandbox.enabled`, `teammateMode`

### Key env vars
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`,
`CLAUDE_CODE_SUBAGENT_MODEL`, `CLAUDE_ENV_FILE`, `ENABLE_TOOL_SEARCH`, `CLAUDE_CODE_NEW_INIT=1`.

## v5.4 gap summary

**HAVE (covered already):**
- PreToolUse(Bash/Write/Edit), PostToolUse(Write/Edit), PreCompact, SessionStart, Stop hooks
- Policy allow/deny (security.yaml) + hook enforcement
- Root CLAUDE.md @-include pattern
- 22 custom agents with YAML frontmatter
- 7 MCP servers inc Graphify
- `.claude/notes/` narrative home + 7 domains + Graphify indexing
- `.mcp.json` at repo root

**GAPS filled in v5.4:**
- `.claude/rules/` path-scoped rules (5 files)
- `Notification`, `PostCompact`, `SessionStart(compact)`, `ConfigChange`, `SessionEnd`,
  `SubagentStart`, `SubagentStop` hook scripts + registration
- `permissions.allow` / `permissions.deny` / `defaultMode` in settings.json
- `autoMemoryEnabled: true` enabled in settings.json
- `.worktreeinclude` at repo root
- `CLAUDE.local.md` template
- Agent frontmatter hardening on governance agents (tools:, model:, memory:, color:)
- `.claude/skills/` scaffold

**DEFERRED (low ROI / experimental):**
- Agent Teams (experimental; enable when needed)
- `/init` with CLAUDE_CODE_NEW_INIT=1 (manual run, not permanent config)
- `UserPromptSubmit`, `UserPromptExpansion`, `PermissionRequest/Denied`,
  `PostToolBatch`, `PostToolUseFailure`, `StopFailure`, `TeammateIdle`,
  `InstructionsLoaded`, `CwdChanged`, `FileChanged`, `WorktreeCreate/Remove`,
  `TaskCreated/Completed`, `Elicitation` — not actively needed; can add when use case surfaces
- Hook types `http`, `prompt`, `agent` — our `command` type is sufficient
- Full skills migration (keeping commands for now; scaffold present)
