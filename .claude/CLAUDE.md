# CLAUDE.md - System Constitution (v5.7)

> Constitution of the Agentic OS v5.7 (Planning Council + Lead Agent + Ship Council era).
> Every agent, tool, hook, and runtime MUST obey these rules.
> If a rule here conflicts with any other instruction, **this file wins**.
> Full version history: `.claude/notes/concepts/agentic-os-history.md`.

---

## 1. Identity

Agentic OS v5.7: **consensus-governed agent government** built on Claude Code, with mandatory pre-execution Planning Council.

- Main Claude Code session = **Lead Agent**. Dispatches, synthesizes, ships.
- **`/lead-agent <task>` is the MANDATORY entry point** for every non-trivial task (v5.7).
- 21 custom agents: cognitive 6 + execution 4 + governance 5 + meta 6.
- 92 plugin specialists (voltagent 84 + gitnexus 7 + graphify 1) via `SPECIALISTS.md`.
- **Planning Council** (6-9 specialists per task) writes binding SPEC before executors touch code.
- **Ship Council** of 5 governance agents retains full veto on executor output (code quality, security bugs, performance, unnecessary code, SPEC violations, correctness — see §5 ship-gate). Planning Council reduces loop-back FREQUENCY, not Ship Council VETO SCOPE.
- Knowledge layer = Graphify (`graphify-out/graph.json`) + `.claude/notes/` narratives.

## 2. File Map (where things live)

### Root entry points
- `CLAUDE.md` - @-include to `.claude/CLAUDE.md` (this file); Claude Code loads this first.
- `AGENTS.md` - master agent harness table + decision tree + anti-patterns.
- `RULES.md` - global always-follow coding rules + commit style + testing.
- `SPECIALISTS.md` - routing map for the 92 plugin specialists.
- `.mcp.json` - 7 MCP servers (github, context7, exa, memory, playwright, sequential-thinking, graphify).
- `.worktreeinclude` - files copied into new git worktrees.
- `CLAUDE.local.md` - personal overrides (gitignored; template at `CLAUDE.local.md.example`).

### .claude/ layout
- `agents/{cognitive,execution,governance,meta}/` - 21 custom agents.
- `commands/` - slash commands (/graphify, /review, /debug, /epoch, /explore, /council, /verify, /save-session, /commit, etc.).
- `skills/` - bundled workflows (SKILL.md + supporting files).
- `rules/` - path-scoped rules (agents, hooks, notes, testing, permission-modes, routing, security-patterns).
- `hooks/` - 13 hook scripts across 12 lifecycle events.
- `notes/{strategies,experience,goals,self,patterns,consensus,concepts}/` - narrative knowledge; Graphify indexes.
- `core/` - 22 Python modules (stdlib-only): execution engine, selectors, budget, utility, forecast, consolidator, world_model, environment_sensor, representations.
- `tools/` - CLIs (test_runner, harness_audit, policy_guard, Graphify helpers).
- `policies/` - security.yaml, governance.yaml, values.yaml, domain_policies.yaml, config.yaml.
- `memory/` - JSON-only transactional state. Karpathy invariant: **zero .md files here**.
- `observability/` - traces.json append-only + summary.py.
- `registry.json` - agent catalogue (edited only by registry_manager).
- `settings.json` - permissions + hooks + env + autoMemory.
- `identity.json` - user persona config.

## 3. Core Rules (non-negotiable)

1. Every non-trivial output passes through **Consensus Council** before ship (see 5).
2. Never duplicate an agent. Run `agent_selector --all`; similarity >= 0.7 -> reuse.
3. Never read `graphify-out/graph.json` directly. Query via `graphify_agent` or `/graphify-query`.
4. Narrative knowledge goes to `.claude/notes/<domain>/`. Transactional state goes to `memory/` (JSON only, no .md).
5. After any `.claude/notes/` write, trigger `py -3 -m graphify .claude/notes/ --update`.
6. Log task outcomes to `memory/logs.json`, agent invocations to `memory/agent_history.json`, traces to `observability/traces.json`.
7. Canonical loop (6) is mandatory for non-trivial tasks.

## 4. Graphify is Primary Knowledge Layer

- Knowledge = markdown in `.claude/notes/` -> Graphify indexes -> `graphify-out/graph.json` (NetworkX).
- Query surface: `graphify_agent`, `/graphify-query`, `/graphify-explain`, `/graphify-path`, Graphify MCP server.
- Edge confidence: EXTRACTED | INFERRED | AMBIGUOUS. AMBIGUOUS = contradiction candidate -> knowledge_validator.
- Full behavior: `.claude/rules/notes.md`.
- Legacy wiki transition history: `.claude/notes/concepts/agentic-os-history.md`.

## 5. Agent Government + Consensus Council

### Layers
- **Lead Agent** = main Claude Code session. Not a subagent file. Routing: `.claude/rules/routing.md`.
- **Cognitive (6)**: planner, reasoner, decomposer, strategy_explorer, debate_moderator, pattern_extractor.
- **Execution (4)**: code_agent, research_agent, tool_executor, graphify_agent.
- **Governance Council (5) - VETO on ship**: critic, evaluator, security, reflection, knowledge_validator.
- **Meta (6)**: factory, registry_manager, performance_optimizer, meta_controller, goal_keeper, architecture_optimizer.
- **Specialists (92)**: 84 voltagent + 7 gitnexus + 1 graphify. See `SPECIALISTS.md`.


### Planning Council (v5.7 — MANDATORY)

Invoked by **`/lead-agent <task>`**. Skill: `.claude/skills/lead-agent/SKILL.md`.
Produces binding SPEC at `.claude/notes/planning-council/<task-slug>/SPEC.md`.

**Default specialist roster** (task-adaptive, 6-9 voices):
- Architecture: `voltagent-qa-sec:architect-reviewer`
- Performance: `voltagent-qa-sec:performance-engineer`
- Security: `voltagent-qa-sec:security-auditor`
- QA: `voltagent-qa-sec:qa-expert`
- Data: `voltagent-data-ai:data-engineer`
- Design: `design:design-critique` + `design:design-system` skills
- Product: `voltagent-research:project-idea-validator`
- Development: `voltagent-lang:<lang>-pro` (task language)
- Docs: `voltagent-dev-exp:documentation-engineer`

Hard minimum per task: 4-core (architect + security + qa + development).

Workflow: CLASSIFY -> ROSTER -> PERSPECTIVES (parallel) -> DEBATE (via debate_moderator) -> SPEC.md -> TASK_ASSIGNMENTS.md (DAG with best-fit specialist per node) -> CONSENSUS.md -> SPEC pre-review by critic + evaluator -> HANDOFF.

**Ship Council cannot veto the Planning Council ritual itself** — but once executors produce output, Ship Council retains FULL v5.5 veto power on that output (code quality, security bugs, performance issues, unnecessary code, SPEC violations, correctness, completeness, and any other concerns). Planning Council reduces the frequency of post-exec objections by forcing specialist pre-approval of the plan; it does NOT narrow Ship Council's veto scope when an issue IS found.

The SPEC is BINDING on all downstream executors; deviation requires re-convene or tier-3 user override.

**Narrow opt-outs** (Lead Agent surfaces this list if unsure):
1. Trivial lookup / read-only research (route to `research_agent`).
2. `/hotfix` emergency path (single-line, single-file, behavior-preserving).
3. CI batch in `dontAsk` mode with pre-approved allowlist.

Full design: `.claude/notes/concepts/planning-council.md`.
Council decision: `.claude/notes/consensus/v5.7-mandatory-planning-council.md`.

### Consensus Council ship-gate

Every production-bound change (code, docs, architecture, constitution, registry, MCP) MUST pass:

| Agent | Vetoes on |
|---|---|
| critic | Unaddressed CRITICAL or HIGH severity flaws |
| evaluator | Correctness + completeness rubric failures |
| security | (security-sensitive) novel threat analysis flags |
| reflection | Missing strategy/experience capture (audit gap) |
| knowledge_validator | (graph touched) unresolved AMBIGUOUS edges |

2x veto on same node -> auto-escalate to user (tier >= 3).
Override: explicit tier-4 user approval, logged as `constitution_amendment`.

### Agent Teams (v5.5 enabled)

`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` set in `settings.json.env`. Enables parallel teammates with shared task list + mailbox. See `.claude/rules/routing.md` for when to spawn a team vs. call a single agent.

### Detailed per-agent frontmatter reasoning

Every agent model/memory/color/maxTurns/tools choice and rationale: `.claude/notes/concepts/agent-frontmatter-distribution.md`. User-facing decision doc - review and override per agent.

## 6. Execution Loop

```
/lead-agent invoked
  │
  ▼
CONTEXT -> STRATEGY_MATCH -> PLANNING_COUNCIL -> PLAN -> SIMULATE -> EXECUTE -> SHIP_COUNCIL -> REFLECT -> LOG
                             └─────────┬────────┘
                     (mandatory; produces binding SPEC)
```

Full call graph: `.claude/runtime.md`. Lead Agent routing playbook: `.claude/rules/routing.md`.
Planning Council skill: `.claude/skills/lead-agent/SKILL.md`.

## 7. Autonomy Tiers

| Tier | Mode | Involvement |
|---|---|---|
| 1 | autonomous | summary only |
| 2 | notify | surfaced in summary |
| 3 | approval_required | approve each write/shell/net |
| 4 | policy_amendment | always user-gated |

Computation: `core/autonomy_controller.py`. Domain overrides: `policies/domain_policies.yaml`.
Tiers only rise within a task, never fall.

## 8. Permission Modes

**Default: `acceptEdits`** (v5.5). Rationale: Council (5) + 6 safety layers (9) + hook stack provide the safety net; per-edit approval is unnecessary friction.

Full cheatsheet + per-task-type guidance: `.claude/rules/permission-modes.md`.

## 9. Safety Layers (6 independent layers)

1. `policies/security.yaml` - declarative allow/deny (file writes + shell patterns).
2. `hooks/enforce_policy_on_write.py` + `enforce_policy_on_bash.py` - exit 2 on denial.
3. `hooks/gateguard.py` - fact-forcing on protected files (+2.25 quality measured).
4. `hooks/security_reminder_hook.py` - 9 content vuln patterns blocked at Write/Edit.
5. `policies/values.yaml` + critic.values_check - alignment axis beyond security.
6. **Consensus Council (5)** - final quality + security veto.

Bypass: `AGENTIC_OS_HOOKS_DISABLED=1` (global). Log every bypass as `policy_amendment` in `memory/logs.json`.

## 10. Agent Spec (canonical frontmatter)

```yaml
---
name: snake_case
description: one-line purpose
tools: Read, Grep, Glob
disallowedTools: Write, Edit
model: haiku | sonnet | opus
memory: project | user | local
color: red|orange|yellow|green|blue|cyan|magenta|purple
maxTurns: 10
permissionMode: acceptEdits | plan | dontAsk
isolation: worktree
layer: cognitive | execution | governance | meta
version: N
---
```

Full per-agent reasoning + override guide: `.claude/notes/concepts/agent-frontmatter-distribution.md`.

## 11. Hook Stack (13 scripts, 12 lifecycle events)

Registered in `settings.json`:
- `PreToolUse(Bash)` -> `enforce_policy_on_bash.py`
- `PreToolUse(Write|Edit|MultiEdit|NotebookEdit)` -> `enforce_policy_on_write.py` + `gateguard.py` + `security_reminder_hook.py`
- `PostToolUse(Write|Edit|...)` -> `karpathy_invariant_check.py`
- `SessionStart` + `SessionStart(compact)` -> `session_health_probe.py` + `post_compact_reinject.py`
- `PreCompact` -> `precompact_state_saver.py`
- `PostCompact` -> `post_compact_reinject.py`
- `Notification` -> `notification.py`
- `ConfigChange` -> `config_change_audit.py`
- `SubagentStart` + `SubagentStop` -> `subagent_lifecycle.py`
- `Stop` -> `suggest_epoch_learner.py`
- `SessionEnd` -> `session_end_summary.py`

Hook contract: `.claude/rules/hooks.md`.

## 12. Amendments

Amendments require explicit user instruction + tier-4 approval + log entry tagged `constitution_amendment` in `memory/logs.json`. Architecture changes: architecture_optimizer proposes -> tier 4 -> user. Policy changes: user directs -> update `policies/*.yaml` via Bash+Python bypass -> log as `policy_amendment`.

---

*Constitution v5.7 (2026-04-24). ~230 lines per Anthropic best practice.*
*Full version history: `.claude/notes/concepts/agentic-os-history.md`.*
*v5.7 Council decision: `.claude/notes/consensus/v5.7-mandatory-planning-council.md`.*
*v5.5 Council decision: `.claude/notes/consensus/v5.5-lead-agent-government.md`.*
