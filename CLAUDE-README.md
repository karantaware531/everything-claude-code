# CLAUDE-README.md — Complete Operator's Guide to the Agentic OS

> If you've never seen this repo before, read this top-to-bottom.
> If you've seen it, use this as a reference — sections are self-contained.
>
> **Current version**: Agentic OS v5.7 (2026-04-24).
> **Status**: 44/44 system checks green, 10/10 harness audit, 6 skills.

---

## Table of contents

0. [TL;DR — what this is](#0-tldr)
1. [Quick start (5 minutes)](#1-quick-start)
2. [Mental model — the government](#2-mental-model)
3. [File map — where everything lives](#3-file-map)
4. [Day-to-day workflows (examples)](#4-workflows)
5. [Complete slash command catalog](#5-slash-commands)
6. [Complete agent catalog](#6-agents)
7. [The 6 safety layers](#7-safety)
8. [Hook system (13 hooks)](#8-hooks)
9. [Permission modes](#9-permission-modes)
10. [Knowledge layer (Graphify)](#10-graphify)
11. [Consensus Council (ship gate)](#11-council)
12. [Agent Teams](#12-agent-teams)
13. [Scheduled routines](#13-routines)
14. [Troubleshooting](#14-troubleshooting)
15. [Configuration reference](#15-config)
16. [Version history](#16-history)
17. [Contributing / amendments](#17-amendments)
18. [Glossary](#18-glossary)

---

<a name="0-tldr"></a>
## 0. TL;DR — what this is

This is a **governed multi-agent system** that sits on top of Claude Code. You ask for work; it dispatches to specialist agents; a council of 5 governance agents blocks ship if anything is wrong. Goal: **you get "best-reasonable" code, not "first-try" code** — nothing ships past the council until it is right.

In numbers:
- **21 custom agents** (cognitive, execution, governance, meta layers).
- **92 plugin specialists** auto-loaded (voltagent 84 + gitnexus 7 + graphify 1).
- **13 hooks** enforcing policy at Claude Code tool boundaries.
- **22 Python core modules** (stdlib only, no pip deps).
- **Graphify knowledge graph** — project notes + code indexed into one queryable graph.
- **Consensus Council** — 5 agents with ship veto. 2× veto auto-escalates to you.

In one metaphor: Claude Code is the OS kernel; this repo is a **government** running on that kernel. Your session is the head of state (the "Lead Agent"). It has ministers (cognitive/meta), workers (execution + 92 specialists), and a supreme court (governance council). You sign off on big decisions; day-to-day is delegated.

---

<a name="1-quick-start"></a>
## 1. Quick start (5 minutes)

### Prerequisites

- **Claude Code** installed (Desktop or CLI; v2.1.32+ for Agent Teams). Get it from `code.claude.com`.
- **Python 3.12+** on PATH as `py -3` (Windows) or `python3` (macOS/Linux).
- **Git**.

### First commands

```bash
# 1. Clone / enter the repo, then:
cd "<path-to-this-repo>"

# 2. Verify system health
py -3 .claude/tools/test_runner.py
# Expected: "44/44 checks passed"

# 3. Harness quality score
py -3 .claude/tools/harness_audit.py
# Expected: "Overall: 10.0/10 (PASS)"

# 4. Initialize project context
#    Inside a Claude Code session, type:
/initialize
```

### Your first task

In a Claude Code session, try:

> "Implement a simple FIFO queue in Python with thread-safety and tests."

What happens:

1. **Lead Agent** (your session) reads boot files (`CLAUDE.md`, `AGENTS.md`, `SPECIALISTS.md`).
2. Dispatches to `voltagent-lang:python-pro` for code + `voltagent-qa-sec:test-automator` for tests.
3. **Consensus Council** (`critic` + `evaluator` + `security`) reviews output.
4. If any council member blocks: loop back to the specialist with findings.
5. When the council is unanimous, the output ships.

Everything logs: `memory/logs.json`, `memory/agent_history.json`, `observability/traces.json`.

---

<a name="2-mental-model"></a>
## 2. Mental model — the government

Five layers — think of a company org chart.

```
┌────────────────────────────────────────────────────────────────┐
│                        YOU (the user)                           │
└────────────────────────────┬───────────────────────────────────┘
                             │ asks for work
┌────────────────────────────▼───────────────────────────────────┐
│  LEAD AGENT  = the main Claude Code session itself.             │
│  Routes per .claude/rules/routing.md.                           │
│  Reads: CLAUDE.md → AGENTS.md → SPECIALISTS.md → registry.json. │
└──┬──────────────┬─────────────────────────────┬───────────────┘
   │              │                             │
   ▼              ▼                             ▼
┌────────┐  ┌────────────┐             ┌─────────────────────┐
│COGNITIVE│  │ EXECUTION  │             │  SPECIALISTS (92)   │
│ (6)     │  │ (4)        │             │  voltagent-lang     │
│planner  │  │ code_agent │             │  voltagent-dev-exp  │
│reasoner │  │ research_* │             │  voltagent-qa-sec   │
│decompo* │  │ tool_exec  │             │  voltagent-data-ai  │
│strategy*│  │ graphify_* │             │  voltagent-research │
│debate_m*│  └────────────┘             │  gitnexus (7)       │
│pattern_*│                             │  graphify (1)       │
└──┬──────┘                             └─────────────────────┘
   │ output
   ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONSENSUS COUNCIL (5) — SHIP VETO                              │
│  critic → red-teams findings (CRITICAL/HIGH/MEDIUM/LOW)         │
│  evaluator → grades correctness + completeness                  │
│  security → novel threat analysis (sensitive domains)           │
│  reflection → captures strategy/experience                      │
│  knowledge_validator → resolves contradictions                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │ unanimous ship
                       ▼
                  SHIPPED
                       │
                       ▼
┌─────────────────────────────────────────────────────────────────┐
│  META (6) — control plane                                        │
│  factory / registry_manager / performance_optimizer              │
│  meta_controller / goal_keeper / architecture_optimizer          │
└─────────────────────────────────────────────────────────────────┘
```

### Layer-by-layer in plain English

- **Lead Agent**: the main Claude window you are talking to. It orchestrates; it does not do the work.
- **Cognitive (6)**: thinks. Planners, decomposers, debaters, pattern finders.
- **Execution (4)**: generic work. Code writes, research, tool runs, graph queries.
- **Specialists (92)**: *domain-specific* work. Python expert, Rust expert, security auditor, performance engineer, etc.
- **Governance Council (5)**: quality gate. NO output ships without unanimous council approval.
- **Meta (6)**: runs the government. Creates new agents, tracks performance, proposes architecture changes.

### How it flows

```
CONTEXT → STRATEGY_MATCH → PLAN → SIMULATE → EXECUTE → CONSENSUS_COUNCIL → REFLECT → LOG
```

1. **CONTEXT**: Lead Agent builds a context bundle.
2. **STRATEGY_MATCH**: ask Graphify "have we solved this task type before?"
3. **PLAN**: `planner` returns a DAG (ordered steps with dependencies).
4. **SIMULATE**: dry-run the plan. Abort if risky.
5. **EXECUTE**: each DAG node. Specialist per domain. Budget tracked.
6. **COUNCIL**: critic → evaluator → (security if needed) → reflection → knowledge_validator.
7. **REFLECT**: capture what worked. Write strategy to `.claude/notes/strategies/`.
8. **LOG**: everything to `memory/logs.json`, `observability/traces.json`.

---

<a name="3-file-map"></a>
## 3. File map — where everything lives

### Repo root (entry points)

```
<repo-root>/
├── CLAUDE.md                    ← @-includes .claude/CLAUDE.md (Claude auto-loads this)
├── CLAUDE-README.md             ← this file
├── AGENTS.md                    ← master agent harness table
├── RULES.md                     ← global always-follow coding rules
├── SPECIALISTS.md               ← routing map for the 92 plugin specialists
├── CLAUDE.local.md              ← your personal overrides (gitignored)
├── CLAUDE.local.md.example      ← template for CLAUDE.local.md
├── .mcp.json                    ← 7 MCP servers
├── .worktreeinclude             ← files copied into new git worktrees
├── case-study/                  ← reusable stress-test demos
└── graphify-out/                ← unified knowledge graph (auto-generated)
    ├── graph.json               ← NetworkX graph
    ├── graph.html               ← interactive visualization
    └── GRAPH_REPORT.md          ← audit report
```

### `.claude/` layout (the OS)

```
.claude/
├── CLAUDE.md                    ← CONSTITUTION (~232 lines, v5.7)
├── registry.json                ← agent catalogue (21 agents)
├── identity.json                ← user persona config
├── settings.json                ← hooks + permissions + env + autoMemory
├── settings.local.json          ← personal overrides (gitignored)
│
├── agents/                      ← 21 custom agents in 4 layers
│   ├── cognitive/ (6)
│   ├── execution/ (4)
│   ├── governance/ (5)
│   └── meta/ (6)
│
├── commands/                    ← slash-command definitions
├── skills/                      ← bundled workflows
│
├── rules/                       ← path-scoped rules (load on demand)
│   ├── README.md, agents.md, hooks.md, notes.md
│   ├── permission-modes.md, routing.md
│   ├── security-patterns.md, testing.md
│
├── hooks/                       ← 13 hook scripts (Python stdlib)
│
├── notes/                       ← narrative knowledge (Graphify indexes this)
│   ├── strategies/              ← winning task sequences
│   ├── experience/              ← distilled lessons
│   ├── goals/                   ← long-term goals
│   ├── self/                    ← system self-model narratives
│   ├── patterns/                ← cross-task abstractions
│   ├── consensus/               ← debate outcomes
│   └── concepts/                ← compiled knowledge + history + proposals
│
├── core/                        ← 22 Python modules (stdlib-only)
│   ├── context_engine.py, execution_engine.py, agent_selector.py
│   ├── scoring_engine.py, autonomy_controller.py, budget_manager.py
│   ├── utility.py, strategy_generator.py, consolidator.py
│   ├── forecast.py, world_model.py, environment_sensor.py
│   ├── epoch_learner.py, reward.py, representations.py, ...
│
├── tools/                       ← CLIs
│   ├── test_runner.py           ← 42-check system gate
│   ├── harness_audit.py         ← 7-category quality scorer
│   ├── policy_guard.py, agent_validator.py
│   ├── nightly_improvement.py   ← daily doc-diff sweep
│
├── policies/                    ← declarative governance
│   ├── security.yaml, governance.yaml, values.yaml
│   ├── domain_policies.yaml, config.yaml
│
├── memory/                      ← JSON-only transactional state (Karpathy invariant)
│   ├── logs.json, agent_history.json, trust_matrix.json
│   ├── goals_state.json, system_profile.json, budgets.json
│
├── observability/
│   ├── traces.json              ← append-only protocol envelope log
│   └── summary.py               ← human-readable stats CLI
│
└── workflows/                   ← pre-baked DAG templates
```

### `~/.claude/` (user-level, Claude Code global)

```
~/.claude/
├── skills/                      ← global skills auto-loaded in every project
├── plugins/cache/               ← installed plugins (voltagent, gitnexus, etc.)
├── teams/                       ← Agent Teams configs
│   └── parallel-code-review/    ← reference config
├── scheduled-tasks/             ← persistent scheduled tasks
│   └── agentic-os-nightly-improvement/SKILL.md
├── session-data/                ← PreCompact state saves
└── settings.json                ← global Claude Code settings
```

### The Karpathy invariant

`.claude/memory/` has **only JSON files** — never `.md`. Narrative knowledge goes into `.claude/notes/<domain>/`. The `karpathy_invariant_check` hook warns if a markdown file appears under `memory/`.

---

<a name="4-workflows"></a>
## 4. Day-to-day workflows (examples)

### Example A: write a new feature

**You say**: "Add rate limiting to the /login endpoint: 5 attempts per 10 minutes per IP."

**What happens**:
1. Lead Agent reads routing rules → domain-specific (auth + rate limit).
2. Checks `SPECIALISTS.md` → picks `voltagent-lang:python-pro`.
3. Graphify query: "any existing rate-limiter strategies in notes/strategies/?"
4. `planner` returns DAG: [research → implement → tests → /verify].
5. Specialist implements. `voltagent-qa-sec:test-automator` writes tests.
6. Council gate: critic + evaluator + security (auth = sensitive).
7. On pass: reflection writes strategy to `.claude/notes/strategies/`.
8. Graphify incremental update indexes the new note.
9. 3-line summary to you + pointer to `traces.json`.

### Example B: fix a bug

**You say**: "/api/orders returns 500 on empty carts."

**What happens**:
1. `/debug` pattern (evidence-first).
2. `research_agent` reads endpoint code + stack trace + tests.
3. Generates minimal reproducer. Writes failing test FIRST.
4. Dispatches to `code_agent` to fix.
5. `/verify` — 6-phase quality gate.
6. Council gates.
7. Reflection writes lesson to `.claude/notes/experience/`.

### Example C: review a PR

Use `/review`.

1. GateGuard hook forces: "list dependencies + affected functions + schema changes".
2. `critic` red-teams diff (severity tags).
3. `evaluator` grades correctness + completeness.
4. `security` checks auth / I/O / net / fs boundaries.
5. Report: `REVIEW VERDICT: PASS | FAIL`, with required fixes.

For deeper parallel review, use Agent Teams (§12).

### Example D: research a topic

**You say**: "Trade-offs between XSalsa20 and AES-256-GCM for at-rest encryption?"

1. Lead picks `voltagent-research:research-analyst`.
2. Specialist uses `WebSearch` + `context7` MCP.
3. `reflection` decides if finding belongs in `.claude/notes/concepts/`.
4. Synthesized answer with citations.

### Example E: ingest a GitHub repo

Use `/graphify <github-url>` or `/graphify-build <path>`.

1. `graphify` clones to `~/.graphify/repos/<owner>/<repo>/`.
2. Full 9-step pipeline: detect → AST + semantic → cluster → analyze → label → export.
3. Graph at `graphify-out/graph.json`, HTML at `graphify-out/graph.html`, audit at `GRAPH_REPORT.md`.
4. Then `/graphify-query "<Q>"` to ask the graph.

### Example F: end-of-day wrap-up

Use `/epoch`.

1. `epoch_learner.py` aggregates last 20 tasks.
2. Updates `memory/system_profile.json`.
3. Writes self-narrative to `.claude/notes/self/`.
4. `forecast.py` projects success_rate, reward, latency.
5. `harness_audit.py` gives 7-category quality score.
6. `consolidator.py` (optional): dedupe + prune.

Summary: "Epoch 12 complete. Weak agents: none. Projected success_rate: 0.87→0.89. Harness: 10/10."

---

<a name="5-slash-commands"></a>
## 5. Complete slash command catalog

All in `.claude/commands/*.md`.

### Project commands

| Command | Purpose |
|---|---|
| **`/lead-agent <task>`** | **v5.7 MANDATORY entry** — Planning Council writes binding SPEC before executors |
| **`/install-plugins`** | **v5.6** — install 9 core plugins by reference (one-time setup) |
| `/initialize` | Scan repo, detect stack, verify registry |
| `/review` | Full quality review: critic + evaluator + security |
| `/debug` | Evidence-first bug diagnosis |
| `/verify` | 6-phase pre-commit quality gate |
| `/ingest <url-or-path>` | Pull GitHub repo or local docs into graph |
| `/epoch` | End-of-epoch learning cycle |
| `/explore <task>` | K-candidate strategy exploration |
| `/council <decision>` | 4-voice adversarial decision framework |
| `/save-session` | 8-section structured session persistence |
| `/nightly-review` | Manually trigger nightly improvement routine |
| `/graphify <path>` | Full graph-build pipeline |
| `/graphify-build` | Shortcut: build from repo root + notes/ |
| `/graphify-query "<Q>"` | BFS/DFS query against graph |
| `/graphify-explain "<node>"` | Node + neighbors explanation |
| `/graphify-path "<A>" "<B>"` | Shortest path between two concepts |
| `/commit` | Structured git commit |
| `/commit-push-pr` | Commit + push + open PR |
| `/clean_gone` | Purge `[gone]` branches + worktrees |

### Project skills (`.claude/skills/*/SKILL.md`)

| Skill | Purpose | When |
|---|---|---|
| `lead-agent` | v5.7 mandatory Planning Council (9-step workflow) | Every non-trivial task |
| `pre-commit-checklist` | 7-point pre-commit gate (tests, secrets, karpathy, SPEC, policy, trace) | Before any commit |
| `spec-first` | Contract-before-code with critic+evaluator sign-off | Before implementing |
| `verification-before-ship` | 8-point gate before declaring "done" | Before PR / commit-push-pr |
| `systematic-review` | 6-lens code review (diff, blame, callers, tests, security, trust) | `/review`, major diffs |
| `graphify-refresh` | Incremental graph update (SHA-cached) | After `.claude/notes/` writes |

### Useful plugin skills (auto-loaded)

| Skill | Purpose |
|---|---|
| `/gitnexus-cli` | Run GitNexus commands |
| `/gitnexus-exploring` | Understand architecture / trace flow |
| `/gitnexus-debugging` | Trace error origin |
| `/gitnexus-impact-analysis` | "What breaks if I change X?" |
| `/gitnexus-refactoring` | Safe rename/extract/move |
| `anthropic-skills:skill-creator` | Create / modify skills |
| `anthropic-skills:mcp-builder` | Build MCP servers |
| `engineering:*` | code-review, architecture, debug, testing-strategy |
| `design:*` | accessibility, design-critique, ux-copy |
| `data:*` | SQL, dashboards, visualization |

---

<a name="6-agents"></a>
## 6. Complete agent catalog

### Our 21 custom agents

#### Cognitive (6) — thinks

| Agent | Role | Model | Color |
|---|---|---|---|
| `planner` | DAG generation | opus | blue |
| `reasoner` | Disambiguates goals | sonnet | cyan |
| `decomposer` | Splits composite tasks | sonnet | cyan |
| `strategy_explorer` | K candidate DAGs ranked by utility | opus | blue |
| `debate_moderator` | Structured multi-agent debate | opus | blue |
| `pattern_extractor` | Finds recurring sub-sequences | sonnet | cyan |

#### Execution (4) — generic work

| Agent | Role | Model | Color |
|---|---|---|---|
| `code_agent` | Generic code write/edit/debug | sonnet | green |
| `research_agent` | Repo + graph + web info gathering | haiku | green |
| `tool_executor` | Run registered CLIs safely | haiku | green |
| `graphify_agent` | Wraps Graphify CLI + MCP | haiku | green |

#### Governance Council (5) — SHIP VETO

| Agent | Vetoes on | Model | Color |
|---|---|---|---|
| `critic` | Unaddressed CRITICAL/HIGH flaws | opus | red |
| `evaluator` | Correctness + completeness failures | sonnet | orange |
| `security` | Novel threats (sensitive domains) | opus | red |
| `reflection` | Missing strategy/experience capture | opus | purple |
| `knowledge_validator` | Unresolved AMBIGUOUS graph edges | sonnet | yellow |

#### Meta (6) — runs the government

| Agent | Role | Model | Color |
|---|---|---|---|
| `factory` | Create new agents under validation | opus | magenta |
| `registry_manager` | Sole editor of registry.json | sonnet | magenta |
| `performance_optimizer` | Aggregate scoring + trust, propose fixes | sonnet | magenta |
| `meta_controller` | Decides tier 1-4 per task | sonnet | magenta |
| `goal_keeper` | Bridges session + long-term goals | sonnet | magenta |
| `architecture_optimizer` | Structural changes (tier 4 always) | opus | magenta |

### 92 plugin specialists (summary)

See `SPECIALISTS.md` for full routing. Quick counts:

- **voltagent-lang (30)**: Python, TypeScript, JS, Go, Rust, Java, C++, C#, Swift, Kotlin, PHP, Ruby, Elixir, Django, Rails, Next.js, React, Vue, Angular, Laravel, Symfony, Spring, Flutter, FastAPI, PowerShell 5.1/7, SQL, .NET Core / Framework.
- **voltagent-dev-exp (15)**: refactoring-specialist, legacy-modernizer, mcp-developer, documentation-engineer, readme-generator, dependency-manager, git-workflow-manager, build-engineer, dx-optimizer, cli-developer, tooling-engineer, slack-expert, PowerShell module/UI.
- **voltagent-qa-sec (16)**: security-auditor, penetration-tester, compliance-auditor, accessibility-tester, chaos-engineer, code-reviewer, debugger, error-detective, performance-engineer, qa-expert, test-automator, ai-writing-auditor, architect-reviewer, AD-security, PowerShell-security-hardening.
- **voltagent-data-ai (14)**: ai-engineer, llm-architect, ml-engineer, data-scientist/analyst/engineer, postgres-pro, database-optimizer, mlops, nlp, prompt-engineer, RL-engineer.
- **voltagent-research (9)**: research-analyst, search-specialist, data/scientific-literature/competitive/market/trend researchers, project-idea-validator.
- **gitnexus (7)**: codebase exploration.
- **graphify (1)**: knowledge-graph pipeline.

### Routing rule

Lead Agent reads `SPECIALISTS.md` on boot. For domain work: prefer voltagent specialist over generic `code_agent`. Governance stays ours — never delegate `critic` / `evaluator` / `security` / `reflection` / `knowledge_validator`.

### Per-agent customization

`.claude/notes/concepts/agent-frontmatter-distribution.md` has the decision table: every `model`, `memory`, `color`, `maxTurns`, `tools` choice with rationale + alternatives + "when to reconsider".

---

<a name="7-safety"></a>
## 7. The 6 safety layers

Before any change ships, it passes 6 independent layers.

### Layer 1 — `policies/security.yaml`
Declarative allow/deny for file writes + shell patterns. The *rulebook*.

Allowlist examples: `.claude/agents/**`, `.claude/notes/**`, `case-study/**`.
Denylist examples: `.env`, `.git/**`, `.claude/CLAUDE.md`, `.claude/policies/**`.

### Layer 2 — `enforce_policy_on_write.py` + `enforce_policy_on_bash.py` hooks
Fire at PreToolUse; exit 2 on denial. The *enforcers*.

### Layer 3 — `gateguard.py` hook
Fact-forcing on protected files. Declare dependencies + affected functions + rollback before edit. Measured impact: +2.25 quality points average.

### Layer 4 — `security_reminder_hook.py` hook
Content scanner at Write/Edit time. Blocks 9 well-known vulnerability pattern categories:

1. Dynamic code evaluation (JS `eval(` variants)
2. Dynamic function construction (JS `new Function(...)`)
3. Shell invocation via Node (`child_process.exec`, sync variant)
4. Shell invocation via Python (`os.system`)
5. Python object-deserialization RCE (standard serializer `pickle`)
6. React HTML-injection prop (`dangerouslySetInnerHTML`)
7. DOM XSS via `.innerHTML`-assignment
8. DOM XSS via legacy `document.write()`
9. GitHub Actions workflow injection (unquoted `${{ github.event.* }}` in `run:`)

Full pattern list lives in the hook source at `.claude/hooks/security_reminder_hook.py`.

### Layer 5 — `policies/values.yaml` + `critic.values_check`
Alignment axis beyond security. Declared values (honesty, transparency, user welfare). Low alignment score → tier ≥ 3.

### Layer 6 — Consensus Council (see §11)
5 governance agents with explicit ship veto. 2× veto auto-escalates to user.

### Bypass (legit tier-4 amendments)

```bash
export AGENTIC_OS_HOOKS_DISABLED=1
```

Every bypass MUST be logged as `policy_amendment` in `memory/logs.json`.

---

<a name="8-hooks"></a>
## 8. Hook system (13 hooks, 12 lifecycle events)

| Event | Hook | What it does |
|---|---|---|
| `SessionStart` | `session_health_probe.py` | Registry/graph/failure-rate banner |
| `SessionStart(compact)` | `post_compact_reinject.py` | Re-inject context after compaction |
| `PreToolUse(Bash)` | `enforce_policy_on_bash.py` | Block denied shell patterns |
| `PreToolUse(Write\|Edit\|MultiEdit\|NotebookEdit)` | `enforce_policy_on_write.py` | Block writes outside allowlist |
| ↑ | `gateguard.py` | Fact-force on protected files |
| ↑ | `security_reminder_hook.py` | Block 9 content vuln patterns |
| `PostToolUse(Write\|Edit\|...)` | `karpathy_invariant_check.py` | Warn on `.md` in `memory/` |
| `PreCompact` | `precompact_state_saver.py` | Save state before compaction |
| `PostCompact` | `post_compact_reinject.py` | Restore context after compaction |
| `Notification` | `notification.py` | Desktop toast for long events |
| `ConfigChange` | `config_change_audit.py` | Log any settings change |
| `SubagentStart` / `SubagentStop` | `subagent_lifecycle.py` | Trace subagent spawn/exit |
| `Stop` | `suggest_epoch_learner.py` | Nudge `/epoch` every 20 invocations |
| `SessionEnd` | `session_end_summary.py` | Clean-exit summary |

### Hook path convention (MANDATORY — v5.5.1)

Every hook command uses `$CLAUDE_PROJECT_DIR` for CWD independence:
```json
{"command": "python \"$CLAUDE_PROJECT_DIR/.claude/hooks/gateguard.py\""}
```

Relative paths are FORBIDDEN (caught by `test_runner.py` check #42).

### Disabling

```bash
export AGENTIC_OS_HOOKS_DISABLED=1     # all hooks off
# or per-hook in settings.local.json
```

---

<a name="9-permission-modes"></a>
## 9. Permission modes

| Mode | Behavior | When to use |
|---|---|---|
| `default` | Ask approval every write/shell/net | First time in an unfamiliar repo |
| **`acceptEdits`** (ours) | Writes + common Bash pass without prompt | **Normal coding sessions** |
| `plan` | Read-only; writes as artifacts only | Risky refactors; security audits |
| `auto` | Background classifier gates each action (Sonnet 4.6+) | Autonomous coding with classifier safety |
| `dontAsk` | Only pre-approved tools run; deny all else | **CI pipelines** |
| `bypassPermissions` | Skips ALL checks except protected paths | **Emergencies only** — log as `constitution_amendment` |

Full cheatsheet: `.claude/rules/permission-modes.md`.

### Switching

- In-session: `/permissions`
- CLI: `claude --permission-mode plan`
- Permanent: `.claude/settings.json` → `permissions.defaultMode`

---

<a name="10-graphify"></a>
## 10. Knowledge layer (Graphify)

Since v5.2, Graphify replaced the legacy LLM Wiki.

```
Writer agent writes markdown
      │
      ▼
.claude/notes/<domain>/<slug>.md
      │ graphify --update (SHA256-cached)
      ▼
graphify-out/graph.json  ← unified NetworkX graph
graphify-out/graph.html  ← interactive visualization
GRAPH_REPORT.md          ← audit: god nodes, surprises
      │ queried by
      ▼
graphify_agent (execution layer)
      │ called by
      ▼
any caller: planner, critic, evaluator, research_agent, etc.
```

### Query

```bash
/graphify-query "what strategies worked for debug tasks?"
/graphify-query "how does reflection reach planner?" --dfs
/graphify-explain "consensus-council"
/graphify-path "reflection" "planner"
```

### Build / rebuild

```bash
/graphify .                                  # full pipeline
py -3 -m graphify .claude/notes/ --update    # incremental
py -3 -m graphify.watch .claude/notes/       # watch mode
```

### Edge confidence

- **EXTRACTED** — deterministic (AST, explicit imports). Confidence 1.0.
- **INFERRED** — LLM semantic. Confidence 0.6–0.9.
- **AMBIGUOUS** — uncertain. Contradiction candidate → `knowledge_validator`. Confidence 0.1–0.3.

### MCP server

Graphify exposes 7 tools via MCP: `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path`. Already wired in `.mcp.json`.

---

<a name="11-council"></a>
## 11. The two councils (v5.7)

v5.7 has TWO councils gating every non-trivial task — one BEFORE code (Planning), one AFTER (Ship).

### Planning Council (pre-execution, v5.7 — MANDATORY)

Entry: `/lead-agent <task>`. Skill: `.claude/skills/lead-agent/SKILL.md`.
9-step workflow: CLASSIFY → ROSTER (6-9 specialists) → PERSPECTIVES (parallel) → DEBATE → SPEC → ASSIGN → CONSENSUS → SPEC PRE-REVIEW → HANDOFF.

| Seat | Focus |
|---|---|
| Architecture | `voltagent-qa-sec:architect-reviewer` |
| Performance | `voltagent-qa-sec:performance-engineer` |
| Security | `voltagent-qa-sec:security-auditor` |
| QA | `voltagent-qa-sec:qa-expert` |
| Data | `voltagent-data-ai:data-engineer` |
| Design | `design:design-critique` + `design:design-system` |
| Product | `voltagent-research:project-idea-validator` |
| Development | `voltagent-lang:<lang>-pro` (task language) |
| Docs | `voltagent-dev-exp:documentation-engineer` |

Artifacts: `.claude/notes/planning-council/<task-slug>/`. SPEC is BINDING on all executors. Deviation requires re-convene or tier-3 user override.

**Ship Council cannot veto the Planning Council ritual itself** — only the SPEC content via critic+evaluator SPEC pre-review at step 8.

### Ship Council (post-execution, v5.5 — full veto retained)

Every production-bound change passes the 5-agent council:

| Seat | Vetoes on |
|---|---|
| `critic` | Unaddressed CRITICAL or HIGH severity flaws (code quality, security bugs, perf, dead code) |
| `evaluator` | Correctness + completeness rubric failures |
| `security` | Novel threat analysis (security-sensitive domains); implementation security review |
| `reflection` | Missing strategy/experience capture |
| `knowledge_validator` | Unresolved AMBIGUOUS graph edges |

Ship Council scope is **unchanged from v5.5** — full power on code quality, security bugs, performance, unnecessary code, SPEC violations, correctness, any other concern. Planning Council reduces loop-back FREQUENCY by pre-approving the approach; it does not narrow Ship Council's scope when implementation issues are found.

### Ship rules

- CRITICAL/HIGH unresolved → block; loop back to worker with findings.
- 2× veto on same node → auto-escalate (tier ≥ 3).
- EU < 0 across plausible paths → raise tier.
- `security_sensitive` domain → min tier 3 always.
- SPEC violation detected → re-convene Planning Council (not inline fix).

### Override

Only user tier-4 approval can override a council veto. Logged as `constitution_amendment`.

### Live demo

See `case-study/sliding-window-rate-limiter/COUNCIL_VERDICT.md`. Round 1 the Ship Council BLOCKED despite 40/40 tests green. Worker looped back, fixed issues, round 2 unanimous SHIP. Real receipts. v5.7's Planning Council frontloads this kind of debate — expected effect: fewer Ship Council loop-backs per task.

---

<a name="12-agent-teams"></a>
## 12. Agent Teams

Enabled via `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json` env.

### When to use

- Parallel code review (security/perf/correctness/style lenses simultaneously).
- Multi-file feature work (one teammate per file).
- Competing debug hypotheses (teammates race to falsify).

### When NOT to use

- Trivial tasks (Teams = ~4× token cost).
- Serial dependencies (use canonical DAG).

### Reference team config

`~/.claude/teams/parallel-code-review/config.json`:

| Teammate | Specialist | Focus |
|---|---|---|
| security-reviewer | `voltagent-qa-sec:security-auditor` | OWASP, auth, secrets |
| performance-reviewer | `voltagent-qa-sec:performance-engineer` | N+1, complexity |
| correctness-reviewer | `voltagent-qa-sec:code-reviewer` | Logic bugs, races |
| style-reviewer | `voltagent-dev-exp:refactoring-specialist` | Readability, naming |

Invocation recipe in the team's `README.md`.

### Limitations (experimental)

- Session state doesn't survive `/resume` or `/rewind`.
- One team per lead session; no nested teams.
- Split-pane broken in VS Code integrated terminal, Windows Terminal, Ghostty.

---

<a name="13-routines"></a>
## 13. Scheduled routines

Persistent scheduled tasks survive Claude Code restarts (unlike session-only `CronCreate`).

### Nightly improvement routine

- **Task ID**: `agentic-os-nightly-improvement`
- **Schedule**: daily 16:11 local (cron `3 16 * * *` + ~8 min jitter)
- **Storage**: `~/.claude/scheduled-tasks/agentic-os-nightly-improvement/SKILL.md`
- **Kill switch**: `AGENTIC_OS_NIGHTLY_DISABLED=1`

### What it does each run

1. Fetches 10 canonical Claude Code docs (`code.claude.com/docs/en/*`).
2. SHA256-diffs vs `memory/nightly_doc_hashes.json`.
3. For changes, writes proposal to `.claude/notes/concepts/proposals/nightly-<YYYY-MM-DD>.md`.
4. Emits 5 protocol envelopes to `observability/traces.json`.
5. Tier 1-2 auto-applied. Tier 3+ surfaced as `PENDING_COUNCIL_DECISION`.
6. Re-runs `test_runner.py` + `harness_audit.py`. Rolls back on regression.
7. Triggers `graphify --update`.

### Managing

| Action | How |
|---|---|
| See next run | Claude Code sidebar → Scheduled |
| Run on demand | Sidebar "Run now" OR `/nightly-review` |
| Disable | `AGENTIC_OS_NIGHTLY_DISABLED=1` OR sidebar toggle |
| Change schedule | `mcp__scheduled-tasks__update_scheduled_task` OR edit SKILL.md |

---

<a name="14-troubleshooting"></a>
## 14. Troubleshooting

### "Stop hook: file not found" — hook lockout

**Symptom**: every tool call fails with `python .claude/hooks/X.py: [Errno 2] No such file or directory`.

**Cause**: CWD drifted outside repo root. Relative hook path now resolves against wrong dir.

**Fix**: hooks already use `$CLAUDE_PROJECT_DIR` in v5.5.1. If this re-appears, from your terminal:

```bash
cd "<repo-root>"
py -3 -c "import json; from pathlib import Path; p=Path('.claude/settings.json'); d=json.loads(p.read_text(encoding='utf-8')); [h.__setitem__('command', h['command'].replace('python .claude/hooks/', 'python \"$CLAUDE_PROJECT_DIR/.claude/hooks/').replace('.py', '.py\"')) for ev in d['hooks'].values() for b in ev for h in b.get('hooks', []) if 'python .claude/hooks/' in h.get('command','')]; p.write_text(json.dumps(d, indent=2), encoding='utf-8'); print('fixed')"
```

Then restart Claude Code.

### Test runner fails

```bash
py -3 .claude/tools/test_runner.py 2>&1 | grep -A2 FAIL

# Common causes:
# - Missing dep (graphifyy not installed) → py -3 -m pip install graphifyy
# - File renamed → update the check in test_runner.py
# - Stale state → rm -rf .claude/__pycache__ graphify-out/.graphify_*
```

### Agent can't write a file

1. Check `security.yaml` allowlist — is the path there?
2. Check `security_reminder_hook` — does content contain a blocked vulnerability pattern?
3. Check `gateguard` — is it a protected file requiring a gate declaration?
4. If legit: Python bypass via Bash (`py -3 -c "open('path').write(content)"`) + log the amendment.

### Graphify query returns nothing

```bash
py -3 -m graphify .claude/notes/ --update    # incremental rebuild
py -3 -m graphify . --mode deep              # full rebuild
```

### Council keeps rejecting

Read the rejection rationale. Common patterns:
- Unaddressed HIGH from `critic` → re-dispatch with the specific finding.
- `evaluator` uncertainty > 0.6 → ambiguous spec; add acceptance criteria.
- `security` novel threat → read description, add mitigation.
- 2× veto → auto-escalated to you; you decide.

---

<a name="15-config"></a>
## 15. Configuration reference

### `.claude/settings.json` keys

| Key | Purpose |
|---|---|
| `permissions.defaultMode` | Default permission mode (`acceptEdits`) |
| `permissions.allow` | Pre-approved commands |
| `permissions.deny` | Hard-blocked commands |
| `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` | `"1"` to enable Agent Teams |
| `autoMemoryEnabled` | Let Claude write cross-session learnings |
| `hooks.<event>` | Array of hook blocks per lifecycle event |

### Environment variables

| Variable | Purpose |
|---|---|
| `AGENTIC_OS_HOOKS_DISABLED=1` | Disable all Agentic OS hooks globally |
| `AGENTIC_OS_GATEGUARD_PROFILE` | `off` / `advisory` (default) / `strict` |
| `AGENTIC_OS_NIGHTLY_DISABLED=1` | Skip the nightly run |
| `AGENTIC_OS_EMBEDDING_BACKEND` | `sha-placeholder` / `keyword-tfidf` |
| `ENABLE_SECURITY_REMINDER=0` | Disable the content scanner (per-session) |
| `CLAUDE_PROJECT_DIR` | Auto-set by Claude Code; used in hook paths |

### Policy files (`.claude/policies/`)

| File | Purpose |
|---|---|
| `security.yaml` | File/shell allow/deny |
| `governance.yaml` | HITL tier escalation |
| `values.yaml` | Declared values + violation patterns |
| `domain_policies.yaml` | Per-task-type tier bumps |
| `config.yaml` | Selector weights, budgets, circuit breaker |

---

<a name="16-history"></a>
## 16. Version history

Full changelog at `.claude/notes/concepts/agentic-os-history.md`. High level:

| Version | Theme |
|---|---|
| v2.0 | Core engine, 4-layer hierarchy, observability, policies, Wiki-is-Primary-Memory |
| v3.0 | Adaptive autonomy: 3 epistemic loops, tiers 1-4, agent merge |
| v4.0 | Self-modeling: system_profile, values, budgets, world_model, debate_moderator |
| v5.0 | Deliberative: utility, K-candidate strategy exploration, pattern_extractor |
| v5.1 | ECC integration: GateGuard (+2.25 quality), Council anti-anchoring, harness_audit |
| v5.2 | Wiki → Graphify migration |
| v5.3 | Specialist Government: 92 plugin specialists |
| v5.4 | Anthropic canonical alignment: rules/, skills/, permissions block |
| v5.4.1 | Security content scanner integrated |
| v5.4.2 | All 22 agents canonicalized |
| **v5.5** | **Lead Agent + Consensus Government**: constitution 725→181 lines, orchestrator retired, Agent Teams |
| **v5.5.1** | Hook path CWD-independence fix; regression check #42 |
| **v5.6** | Plugin install-by-reference: `plugins-manifest.json` + `/install-plugins` + check #43 |
| **v5.7** | **Planning Council mandatory**: `/lead-agent` entry point; 6-9 specialists pre-exec; SPEC binding; Ship Council full veto scope retained; check #44; 4 new discipline skills (pre-commit-checklist, spec-first, verification-before-ship, systematic-review) |

---

<a name="17-amendments"></a>
## 17. Contributing / amendments

### Autonomy tiers

| Tier | Mode | Involvement |
|---|---|---|
| 1 | autonomous | Summary only |
| 2 | notify | Surfaced in summary |
| 3 | approval_required | You approve each write/shell/net |
| 4 | policy_amendment | Always user-gated |

Tiers only rise within a task, never fall.

### Changing something

| What | Path | Who approves |
|---|---|---|
| New agent | `factory` → `agent_validator` → `registry_manager` | tier 3 |
| Amend agent prompt | `reflection` proposes → `registry_manager` applies | tier 3 |
| Change a hook | Edit `hooks/X.py` + update `settings.json` | tier 3 |
| Change `security.yaml` | Direct edit + log as `policy_amendment` | tier 4 |
| Change constitution | Python bypass + log as `constitution_amendment` | tier 4 |
| Architecture change | `architecture_optimizer` proposes + tier 4 approval | tier 4 |

### Audit trail

Every amendment in `memory/logs.json`:
- `task_id`, `timestamp`, `outcome`, `tier`, `detail`, `affected_files`.

### Consensus decisions

Major architectural decisions persisted to `.claude/notes/consensus/`:
- `v5.3-specialist-integration.md`
- `v5.4-anthropic-best-practices.md`
- `v5.5-lead-agent-government.md`
- `v5.7-mandatory-planning-council.md`
- `v5.6-council-decisions.md`

Each contains 4-voice Council verdicts + approved actions + reopen conditions.

---

<a name="18-glossary"></a>
## 18. Glossary

| Term | Meaning |
|---|---|
| **Agent** | Subagent with `.md` file in `.claude/agents/` + entry in `registry.json`. Invoked via `Task` tool. |
| **Agent Teams** | Experimental Claude Code v2.1.32+ feature for parallel teammates. |
| **Caveman mode** | Terse, low-token output style the user can request. |
| **Consensus Council** | 5 governance agents with ship veto. |
| **DAG** | Directed Acyclic Graph. Planner returns one per task. |
| **GateGuard** | PreToolUse hook forcing fact-declaration before edits to protected files. |
| **Graphify** | Python package building the unified knowledge graph. |
| **Hook** | Python script fired on Claude Code lifecycle event. |
| **Karpathy invariant** | `.claude/memory/` = JSON only, never markdown. |
| **Lead Agent** | Main Claude Code session (no subagent file). Dispatches work. |
| **Loop-back** | Council rejection → worker revises → Council re-reviews. |
| **MCP** | Model Context Protocol. |
| **Meta layer** | 6 agents running the government itself. |
| **Protocol envelope** | Standard message format between agents; one per call in `traces.json`. |
| **Reflection loop** | After every task, extract strategy + experience to `.claude/notes/`. |
| **Ship veto** | Council member's authority to block output from reaching the user. |
| **Specialist** | One of 92 voltagent/gitnexus/graphify plugin agents. |
| **Strategy** | Winning agent sequence for a task type, in `.claude/notes/strategies/`. |
| **Tier** | Autonomy level 1-4 per task. |
| **Trace** | Protocol envelope in `observability/traces.json`. |

---

## Need help? Debug checklist

1. `py -3 .claude/tools/test_runner.py` — 44/44 green?
2. `py -3 .claude/tools/harness_audit.py` — 10/10?
3. Recent amendments: `cat .claude/memory/logs.json | python -m json.tool | tail -50`.
4. Recent agent calls: `cat .claude/observability/traces.json | python -m json.tool | tail -100`.
5. Latest consensus: `.claude/notes/consensus/v5.6-council-decisions.md`.
6. Constitution: `.claude/CLAUDE.md` (181 lines — it's short).

If those are fine, look for receipts:
- Council rejection → `traces.json` entry with `"verdict": "FAIL"` or `"BLOCK"`.
- Hook block → Claude Code error banner starting with `[hook:<name>]`.
- Failed test → `test_runner.py` output.

Everything leaves receipts. If you can't find one, issue is outside the system (env var, file permissions, shell quoting).

---

*CLAUDE-README.md v1.1, updated 2026-04-24. Covers Agentic OS v5.7.*
*Machine-readable rules: `.claude/CLAUDE.md`. History: `.claude/notes/concepts/agentic-os-history.md`.*
