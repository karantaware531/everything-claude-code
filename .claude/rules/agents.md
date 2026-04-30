---
paths:
  - ".claude/agents/**/*.md"
---

# Agent Markdown Conventions

When editing any file under `.claude/agents/**/*.md`:

## Required frontmatter fields
- `name` — snake_case, matches filename
- `description` — one-line purpose; first 140 chars appear in UI
- `layer` — one of `cognitive | execution | governance | meta`
- `version` — integer; bump on substantive changes

## Recommended frontmatter fields (Anthropic canonical)
- `tools` — explicit allowlist (use `Read, Grep, Glob` for read-only agents)
- `disallowedTools` — explicit denylist (e.g., `Write, Edit` on governance agents)
- `model` — `haiku | sonnet | opus` (cost optimization)
- `permissionMode` — `default | acceptEdits | plan | dontAsk`
- `memory` — `user | project | none` (persistent cross-session memory scope)
  - `memory: user` → stores in `~/.claude/agent-memory/` (all projects)
  - `memory: project` → stores in project root memory dir (repo-scoped)
  - `memory: none` → no persistent memory (default for most agents)
- `maxTurns` — integer cap on agent self-chat (prevents runaway)
- `color` — UI distinguisher in task lists
- `isolation` — `worktree` for risky parallel edits (git worktree per invocation)
- `effort` — `low | medium | high | xhigh` effort level (Opus 4.7 only for xhigh)
- `background` — `true` to run without blocking orchestrator (async dispatch)
- `skills` — list of skill names to inject at subagent startup (e.g., `[lead-agent]`)
- `initialPrompt` — string injected as first context before task (domain bootstrapping)

## Governance agents (critic, evaluator, security, reflection, knowledge_validator)
- MUST have `tools: Read, Grep, Glob` (read-only)
- MUST have `memory: project` (they accumulate cross-session knowledge)
- MUST have `color: red` or similar distinguishable color
- Never route specialist-domain work to governance agents; they validate, not produce.

## Body conventions
- First H1 is the agent name, human-readable.
- Section order: Mission → When you run → Inputs → Outputs → Procedure → Hard rules → See also.
- `See also` uses `[[wiki-links]]` for Graphify semantic extraction.

## Registration
Every agent file must correspond to an entry in `.claude/registry.json`.
Registry is edited by `registry_manager` only.
