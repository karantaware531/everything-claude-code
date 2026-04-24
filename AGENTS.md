# AGENTS.md — Master Agent Harness Table

> Primary harness instruction file for the Agentic OS v5.7 (Planning Council + Lead Agent + Ship Council era).
> Delegates every task type to the right specialist. Read this before invoking any agent.
> Constitution: `.claude/CLAUDE.md` | Usage guide: `.claude/USAGE.md` | Full history: `.claude/notes/concepts/agentic-os-history.md`
>
> **v5.7 change (2026-04-24):** `/lead-agent <task>` is the MANDATORY entry point for every
> non-trivial task. Planning Council (6-9 specialists: architecture, performance, security,
> QA, data, design, product, development, docs) writes a binding SPEC before executors touch
> code. Ship Council (v5.5, 5 governance agents) retains full post-exec veto scope on code
> quality / security / performance / correctness / SPEC violations. Ship Council cannot veto
> the Planning Council ritual itself — only its SPEC content.
> **v5.5 change:** Orchestrator retired. The main Claude Code session IS the Lead Agent.
> `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` enabled. Default permission mode = `acceptEdits`.
> 21 custom agents.

---

## The Golden Rule (v5.7)

**The main Claude Code session IS the Lead Agent.** It reads `.claude/rules/routing.md` +
`.claude/skills/lead-agent/SKILL.md` + `SPECIALISTS.md` + this file, then dispatches.
No `orchestrator` subagent wrapper.

Every non-trivial task starts with **`/lead-agent <task>`** — this triggers the
Planning Council (pre-execution specialist debate). Every production-bound output
subsequently passes through the **Ship Council of 5** before ship:
`critic` → `evaluator` → (if sensitive) `security` → (if graph touched) `knowledge_validator` → `reflection`.

> **v5.3 specialist government**: 84 voltagent + 7 gitnexus + 1 graphify are auto-loaded via plugins. See **[`SPECIALISTS.md`](SPECIALISTS.md)** for the full routing map. Governance (this file's 21 agents) stays ours; specialists do the domain-specific work.

---

## Layer 0 — Lead Agent (v5.7)

The **main Claude Code session** plays this role. Not a subagent file.
Routing logic: `.claude/rules/routing.md`. Reads this file + SPECIALISTS.md + registry on boot.
Entry point: **`/lead-agent <task>`** — invokes the Planning Council skill
(`.claude/skills/lead-agent/SKILL.md`), which assembles 6-9 specialists, runs debate, writes
binding SPEC + TASK_ASSIGNMENTS + CONSENSUS, then hands approved DAG to executors.
Post-execution, Ship Council (5 governance agents) judges the output at full scrutiny.

### Planning Council (v5.7 — MANDATORY pre-exec layer)

| Role | Default specialist / skill |
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

Hard minimum per task: 4-core (architect + security + qa + development).
Opt-outs: trivial lookup, `/hotfix`, CI batch in `dontAsk`.
Artifacts: `.claude/notes/planning-council/<task-slug>/`.

## Layer 1 — Meta (Control Plane, 6 agents — orchestrator retired v5.5)

| Agent | Trigger | Invoke when… | Location |
|---|---|---|---|
| **meta_controller** | Every task (automatic) | Decides autonomy tier 1-4 | `.claude/agents/meta/meta_controller.md` |
| **goal_keeper** | Subgoal changes | Track goal state + long-term wiki | `.claude/agents/meta/goal_keeper.md` |
| **factory** | New capability needed | Create a new agent (checks registry first) | `.claude/agents/meta/factory.md` |
| **registry_manager** | Agent registration/amendment | Sole editor of `.claude/registry.json` (moved from wiki/ in v5.2) | `.claude/agents/meta/registry_manager.md` |
| **performance_optimizer** | Weekly / on alert | Analyse scoring + trust; propose fixes | `.claude/agents/meta/performance_optimizer.md` |
| **architecture_optimizer** | Structural change proposal | Tier 4 always — propose, never self-apply | `.claude/agents/meta/architecture_optimizer.md` |

---

## Layer 2 — Cognitive (Planning & Deliberation)

| Agent | Trigger | Invoke when… | Location |
|---|---|---|---|
| **planner** | After orchestrator routing | Turn goal into executable DAG | `.claude/agents/cognitive/planner.md` |
| **reasoner** | Ambiguous goal | Disambiguate + recommend direction | `.claude/agents/cognitive/reasoner.md` |
| **decomposer** | Multi-part DAG node | Split composite into atomic capabilities | `.claude/agents/cognitive/decomposer.md` |
| **strategy_explorer** | High-stakes task (tier ≥ 3) | Generate K candidate DAGs, rank by utility | `.claude/agents/cognitive/strategy_explorer.md` |
| **debate_moderator** | Disagreement / uncertainty ≥ 0.6 | Run proposer → critic → resolver protocol | `.claude/agents/cognitive/debate_moderator.md` |
| **pattern_extractor** | Every 5+ strategies accumulated | Find recurring sub-sequences → wiki/patterns/ | `.claude/agents/cognitive/pattern_extractor.md` |

---

## Layer 3 — Execution (Doing the Work)

| Agent | Trigger | Invoke when… | Location |
|---|---|---|---|
| **code_agent** | Code write/edit/debug task | Write, edit, or fix source code | `.claude/agents/execution/code_agent.md` |
| **research_agent** | Information gathering | Search the graph + repo; read files; return findings (routes through `graphify_agent`) | `.claude/agents/execution/research_agent.md` |
| **tool_executor** | Tool invocation needed | Invoke registered tools safely | `.claude/agents/execution/tool_executor.md` |
| **graphify_agent** (v5.2) | Any knowledge query | Query unified graph; trigger rebuilds after `.claude/notes/` writes | `.claude/agents/execution/graphify_agent.md` |

---

## Layer 4 — Governance (Quality & Safety)

| Agent | Trigger | Invoke when… | Location |
|---|---|---|---|
| **critic** | Before evaluator (automatic) | Red-team any agent output; find flaws | `.claude/agents/governance/critic.md` |
| **evaluator** | After critic (automatic) | Grade correctness, completeness, hallucination risk | `.claude/agents/governance/evaluator.md` |
| **security** | Novel/ambiguous threat | Contextual security reasoning beyond policy_guard | `.claude/agents/governance/security.md` |
| **reflection** | After every task | Write strategies/experience to `.claude/notes/`; trigger graphify update | `.claude/agents/governance/reflection.md` |
| **knowledge_validator** | Contradiction detected (AMBIGUOUS edge in graph) | Resolve notes/graph contradictions via authority scoring | `.claude/agents/governance/knowledge_validator.md` |

---

## ECC Quality Patterns (Invoke by slash command)

| Pattern | Command | What it does | Measured impact |
|---|---|---|---|
| **Lead Agent** (v5.7) | `/lead-agent <task>` | **MANDATORY** — Planning Council writes binding SPEC before executors | Frontloads specialist debate; reduces post-exec loop-backs |
| **GateGuard** | *(automatic PreToolUse hook)* | Forces fact investigation before any edit | +2.25 quality points avg |
| **Council** | `/council <decision>` | 4-voice adversarial decision (anti-anchoring) | Best for: fork decisions |
| **Verify** | `/verify` | 6-phase quality gate: build/type/lint/test/sec/diff | Release gate |
| **Harness Audit** | `/harness-audit` | 7-category system quality score | Weekly health check |
| **Install Plugins** | `/install-plugins` | Install 9 core plugins by reference | One-time setup |
| **Save Session** | `/save-session` | 8-section structured session persistence | Long session continuity |

## Graphify Knowledge Commands (v5.2)

| Command | What it does |
|---|---|
| `/graphify` (full skill) | Complete build pipeline: detect → AST + semantic → cluster → analyze → HTML + JSON + report |
| `/graphify-build` | Shortcut: build graph from repo root + `.claude/notes/` |
| `/graphify-query "<Q>"` | BFS/DFS traversal query against the graph (add `--dfs` for path-tracing) |
| `/graphify-explain "<node>"` | Plain-language explanation of a single node + its neighbors |
| `/graphify-path "<A>" "<B>"` | Shortest path between two concepts |

---

## Decision Tree: Which Agent? (v5.7)

```
Task arrives
│
├─ Trivial (single file, known change, < 5 lines) ──────→ code_agent directly
├─ Read-only lookup / research ──────────────────────────→ research_agent directly
├─ Single-line hotfix (behavior-preserving) ─────────────→ code_agent + /hotfix label
│
├─ Non-trivial (multi-step / new capability / wide) ─────→ /lead-agent <task>  [MANDATORY v5.7]
│                                                           ↓
│                                                           Planning Council (6-9 specialists)
│                                                           ↓
│                                                           binding SPEC + TASK_ASSIGNMENTS
│                                                           ↓
│                                                           planner THIN-synthesizes DAG
│                                                           ↓
│                                                           executors (per SPEC owner assignments)
│                                                           ↓
│                                                           Ship Council (5 governance agents)
│
├─ Architectural (consolidation, layer change) ──────────→ architecture_optimizer [tier 4]
├─ Two agents disagree / uncertainty ≥ 0.6 ─────────────→ debate_moderator
├─ Binary decision (fork / technology choice) ───────────→ /council
├─ New capability gap ────────────────────────────────────→ factory (after similarity check)
├─ Knowledge contradiction (AMBIGUOUS edge in graph) ───→ knowledge_validator
└─ "What do we know about X?" (knowledge query) ─────────→ graphify_agent  or  /graphify-query "X"
```

---

## Anti-Patterns (Never Do)

- **Never skip `/lead-agent` on a non-trivial task.** Unless one of the 3 opt-outs applies (trivial lookup / `/hotfix` / CI `dontAsk`), go through Planning Council.
- **Never modify a binding SPEC mid-execution.** Re-convene Planning Council instead.
- **Never bypass critic + evaluator (Ship Council).** Every agent output must be graded post-exec.
- **Never create a new agent without running `agent_selector --all` first.** Similarity ≥ 0.7 → reuse.
- **Never invoke code_agent on an ambiguous task.** Route through `/lead-agent` (or `reasoner` if pre-Planning-Council disambiguation needed).
- **Never read `graphify-out/graph.json` directly.** Query through `graphify_agent` so confidence tags are respected.
- **Never run architecture changes autonomously.** Always tier 4 → user approval.

---

## Autonomy Tiers Quick Reference

| Tier | Name | When triggered | User involvement |
|---|---|---|---|
| 1 | autonomous | Low uncertainty + low risk | Summary only |
| 2 | notify | Medium uncertainty OR debug domain | Surfaced in summary |
| 3 | approval_required | High uncertainty OR security domain | Approve before write/shell/net |
| 4 | policy_amendment | Constitution/policy/registry edits | Always user-gated |

Domain overrides: `security_sensitive` → min tier 3. `architecture_modification` → min tier 4. See `.claude/policies/domain_policies.yaml`.

---

## MCP Live Data Sources

Configured in `.mcp.json`. Available in every session:

| Server | What it provides |
|---|---|
| `github` | PR diffs, issues, repo search |
| `context7` | Up-to-date library docs (no hallucinated APIs) |
| `exa` | Real-time web search |
| `memory` | Cross-session persistent memory store |
| `playwright` | Browser automation + E2E test support |
| `sequential-thinking` | Step-by-step reasoning scaffolding |
| `graphify` (v5.2) | Live query into `graphify-out/graph.json` — `query_graph`, `get_node`, `get_neighbors`, `get_community`, `god_nodes`, `graph_stats`, `shortest_path` |
