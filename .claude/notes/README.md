# .claude/notes/ — Agent Narrative Write Destination (v5.2 Graphify era)

> As of Agentic OS v5.2 (2026-04-24), the LLM Wiki was removed. This directory
> replaces it for **session-generated agent narratives**. Graphify indexes this
> folder (plus the repo root) into a unified knowledge graph at
> `graphify-out/graph.json`.

## Structure

| Folder | Written by | Purpose |
|---|---|---|
| `strategies/` | `reflection` | Winning task sequences — planner seeds from these |
| `experience/` | `reflection` | Distilled lessons from failures + surprises |
| `goals/` | `goal_keeper` | Long-term project goals + subgoal tracking |
| `self/` | `epoch_learner` | System self-model narratives per epoch |
| `patterns/` | `pattern_extractor` | Cross-task agent-sequence abstractions |
| `consensus/` | `debate_moderator` | Persistent debate outcomes + reopen conditions |
| `concepts/` | `graphify_agent` (on `--add`) | Free-form compiled concepts (replaces `wiki/concepts/`) |

## How knowledge now flows

```
Agent (reflection/goal_keeper/...)
    │
    │  writes markdown file
    ▼
.claude/notes/<domain>/<slug>.md
    │
    │  Graphify ingests (watch mode, git hook, or /graphify --update)
    ▼
graphify-out/graph.json      ← unified knowledge graph
graphify-out/graph.html      ← interactive visualization
graphify-out/GRAPH_REPORT.md ← audit report with god nodes + surprises
    │
    │  queried by
    ▼
graphify_agent  (execution layer; wraps Graphify CLI + MCP)
    │
    ▼
any caller (orchestrator, planner, critic, evaluator, …)
```

## Rules

1. **Agents write markdown here; Graphify handles the rest.** No hand-rolled
   graph updates, no `wiki_compiler.py`, no `wiki_updater/wiki_curator` chain.

2. **Each note is self-contained.** Include provenance (task_id, timestamp,
   contributing agents) in frontmatter so Graphify can tag edges.

3. **One concept per file.** Update in place when revisiting the same concept
   (Graphify's SHA256 cache handles incremental re-indexing).

4. **Link via `[[wiki-links]]`.** Graphify picks these up as edge hints during
   semantic extraction.

5. **Confidence tagging.** Graphify auto-tags edges as EXTRACTED / INFERRED /
   AMBIGUOUS. You don't need to hand-mark contradictions — AMBIGUOUS surfaces
   them automatically.

## Frontmatter convention

```yaml
---
domain: strategies|experience|goals|self|patterns|consensus|concepts
slug: short-kebab-case-identifier
task_id: t-<id>         # if session-generated
agents: [reflection, code_agent]   # list of contributing agents
first_observed: 2026-04-24T10:00:00Z
last_updated: 2026-04-24T10:00:00Z
confidence: 0.8         # 0.0-1.0, agent's confidence in this narrative
supersedes: []          # list of slugs this entry replaces (if any)
---
```

## Rebuild command

```bash
# Full rebuild (re-extracts everything)
python -m graphify . --obsidian

# Incremental (only changed files)
python -m graphify . --update

# Watch mode (auto-rebuild on file change)
python -m graphify . --watch
```

## Query commands (via global /graphify skill or project-local graphify_agent)

```bash
# Broad context
/graphify query "what strategies worked for debug tasks?"

# Specific path
/graphify path "reflection" "planner"

# Single node deep-dive
/graphify explain "code-review-pattern"
```
