# USAGE.md — Operator's Guide (Agentic OS v5)

> How to actually use, maintain, and grow the system.
> Complements `CLAUDE.md` (the rules) and `runtime.md` (the loop).

---

## 0 · First-time orientation

Before anything else:

```bash
# 1. Verify the system is healthy — expect 27/27 PASS
python .claude/tools/test_runner.py

# 2. See the agent surface — expect 23 agents, all OK
python .claude/tools/agent_validator.py --self-test

# 3. Read the contract, in this order:
#    - .claude/CLAUDE.md                    (rules, limits, Karpathy invariant)
#    - .claude/runtime.md                   (canonical loop + call graph)
#    - .claude/core/agent_protocol.md       (message envelope schema)
```

Run the slash command once:

```
/initialize
```

It scans the repo, detects the stack, writes `project_overview.md` at the repo root, verifies the registry, and logs the boot.

---

## 1 · Three ways to use the system

### A. Delegate to the orchestrator (preferred for real work)

In Claude Code, invoke the `orchestrator` subagent and describe what you want done:

> "Use the orchestrator agent to add input validation to `parse_config.py`."

The pipeline handles the rest:

```
context_engine → goal_keeper → meta_controller → planner
  → (strategy_explorer if tier ≥ 3)
  → execution_engine → [code_agent | research_agent | tool_executor]
  → critic → evaluator
  → wiki_updater → wiki_compiler → wiki_curator
  → scoring_engine → trust_matrix → traces.json
  → reflection (strategies, experience, goal progress, contradictions)
```

### B. Invoke tools directly (for ingestion + administration)

```bash
# Pull knowledge from a GitHub repo into the wiki
python .claude/tools/repo_ingestor.py --url https://github.com/OWNER/REPO

# Check semantic similarity before asking factory for a new agent
python .claude/core/agent_selector.py \
    --capability "summarise pdf" --task "turn a paper into concept notes" --all

# Simulate a plan without running it
python .claude/core/execution_engine.py --simulate \
    --plan-file .claude/workflows/codegen_pipeline.json
```

### C. Use workflow templates for recurring task types

`.claude/workflows/{codegen,debug,rag}_pipeline.json` are pre-baked DAGs. Validate, then feed to the orchestrator:

```bash
python .claude/core/execution_engine.py --simulate --plan-file .claude/workflows/debug_pipeline.json
# → then ask orchestrator to run it
```

---

## 2 · Growing the LLM Wiki — 4 procedures

**The rule: compile, never consume raw.** Every knowledge artefact enters via `wiki_compiler.py --domain <d>`.

### 2.1 · Ingest a GitHub repo

```bash
python .claude/tools/repo_ingestor.py --url https://github.com/OWNER/REPO
```

Flow: shallow clone → bundle README + curated source files into `wiki/raw/github/<owner>-<repo>-<timestamp>.md` → auto-invoke `wiki_compiler` which produces concept files, updates `wiki/graph/graph.json`, writes a summary. Never edit `wiki/raw/**` after ingestion — it's immutable.

### 2.2 · Ingest local documentation (papers, PDFs, notes)

```bash
# Stage the raw file (wiki/raw/ is immutable; always write fresh, never edit)
cp ~/Downloads/paper-notes.md .claude/wiki/raw/papers/transformer-attention.md

# Compile into the concepts domain
python .claude/tools/wiki_compiler.py \
    --raw .claude/wiki/raw/papers/transformer-attention.md \
    --domain concepts
```

### 2.3 · Record a winning strategy (after a successful task)

Reflection does this automatically at the end of a task. Manual form:

```bash
cat > .claude/wiki/raw/docs/strategy-debug-python-error.md << 'EOF'
# Strategy: Debug Python Error

## Summary
When Python raises with a clear traceback, gather evidence first, then patch.

## Winning sequence
1. [[research_agent]]
2. [[code_agent]]
3. [[evaluator]]

## Trigger pattern
error message + file path
EOF

python .claude/tools/wiki_compiler.py \
    --raw .claude/wiki/raw/docs/strategy-debug-python-error.md \
    --domain strategies
```

Subsequent `planner` invocations will seed from this strategy when the task type matches.

### 2.4 · Distill a lesson (`experience` domain)

```bash
python .claude/tools/wiki_compiler.py \
    --raw .claude/wiki/raw/docs/lesson-large-diffs-break-code-agent.md \
    --domain experience
```

### The 7 knowledge domains

| Domain | Purpose | Writer |
|--------|---------|--------|
| `concepts` | General knowledge | `wiki_updater` |
| `strategies` | Winning task sequences | `reflection` |
| `experience` | Distilled lessons | `reflection` |
| `goals` | Long-term goals | `goal_keeper` |
| `self` | Distilled self-claims | `reflection` + `epoch_learner` |
| `patterns` | Cross-task abstractions | `pattern_extractor` |
| `consensus` | Persistent debate outcomes | `debate_moderator` |

---

## 3 · Maintenance cadence

| When | Command | Why |
|------|---------|-----|
| **After every non-trivial task** | _(automatic via `reflection`)_ | Strategies, experience, goal progress compound |
| **~Every 20 tasks** | `python .claude/core/epoch_learner.py --window 20` | Update `memory/system_profile.json` + stage `wiki/self/` narrative |
| **Weekly** | `python .claude/observability/summary.py` | Per-agent pass rate, latency, recent failures |
| **Weekly** | `python .claude/core/forecast.py --metric success_rate --horizon 10` | Spot declining trends early |
| **Weekly** | `python .claude/core/consolidator.py --dry-run` | Review near-duplicate merges + graph decay |
| **Monthly** | `python .claude/core/consolidator.py --apply` | Execute consolidation (after reviewing dry-run) |
| **Monthly** | `python .claude/tools/test_runner.py` | Confirm 27/27 green |
| **On-demand** | invoke `pattern_extractor` | Find cross-task abstractions once you have ≥ 5 strategies |
| **On-demand** | invoke `architecture_optimizer` | Structural change proposals (tier 4 — always user-approved) |

### Populate the IDF corpus (occasional)

Improves `keyword-tfidf` embedding quality:

```bash
# Unix / git-bash — shell loop over raw files
for f in .claude/wiki/raw/**/*.md; do
    python .claude/core/representations.py --corpus-update "$(cat "$f")" > /dev/null
done

# Then activate the semantic backend for this session
export AGENTIC_OS_EMBEDDING_BACKEND=keyword-tfidf
```

---

## 4 · Health checks

```bash
# Full suite — single source of truth for system health
python .claude/tools/test_runner.py

# Graph surface (nodes, edges, types)
python .claude/core/graph_query.py --stats

# Per-agent stats
python .claude/core/scoring_engine.py --stats <agent_name>

# Autonomy tier decision for a hypothetical task
python .claude/core/autonomy_controller.py \
    --task "refactor auth module" --uncertainty 0.4 --risk medium --domain codegen

# Environment probe (cached 5 min; --force bypasses)
python .claude/core/environment_sensor.py --probe

# Policy check before a proposed action
python .claude/tools/policy_guard.py --action "write:.claude/agents/foo.md"
python .claude/tools/policy_guard.py --action "shell:git status"
```

---

## 5 · Housekeeping

Reset leftover transactional state (safe — does not touch wiki/):

```bash
# Preview what would be reset
python .claude/tools/reset_test_state.py --dry-run

# Actually reset
python .claude/tools/reset_test_state.py --apply

# Also delete wiki smoke-test concepts (one-off cleanup after bootstrap)
python .claude/tools/reset_test_state.py --apply --include-wiki-smoke
```

Refuses to run if it detects real data (epoch_count > 0, >10 sim entries, unknown task_ids).

---

## 6 · Tips & gotchas

### DO
- **Answer from compiled concepts**, never from `wiki/raw/**` — the Karpathy invariant.
- **Use the orchestrator agent** as the front door for anything non-trivial. Resist direct execution-agent calls.
- **Keep `memory/` JSON-only.** If you're writing narrative, it belongs in `wiki/`.
- **Let reflection run.** The strategies/experience/self pages only compound when you complete tasks end-to-end.
- **Check the autonomy tier** before acting on high-risk changes.
- **Populate the IDF corpus** after ingesting new documents — it substantially improves keyword-TFIDF similarity.

### DON'T
- Edit `.claude/CLAUDE.md`, `.claude/policies/**`, `.claude/wiki/raw/**`, or `registry.json` by hand. Tier 3–4.
- Bypass the semantic similarity check when asking factory for a new agent.
- Silently ignore `test_runner` failures. Red = drift.
- Grant `Write` or `Bash` to a new agent without a written `constraints` justification.

### Debugging signals
| Signal | Action |
|--------|--------|
| `summary.py` shows `fails > passes` for an agent | Propose amendment via `registry_manager` |
| `forecast` projects `success_rate < 0.5` | Ask `performance_optimizer --mode global` |
| `consolidator --dry-run` reports `verbose_summaries` | Ask `reflection` to rewrite |
| Concept carries `> ⚠️ Contradiction:` | Hand to `knowledge_validator` |
| `autonomy_controller` returns tier 4 | Stop; get user approval before any action |

---

## 6.5 · Hook enforcement layer (v5.1)

Claude Code hooks in `.claude/settings.json` **actively enforce** `security.yaml`
at the tool boundary. They upgrade `policy_guard` from advisory to enforced.

| Event | Hook | What it does |
|-------|------|--------------|
| `SessionStart` | `session_health_probe.py` | Emits registry + graph + failure-rate banner. Never blocks. |
| `PreToolUse(Bash)` | `enforce_policy_on_bash.py` | Calls `policy_guard --action "shell:<cmd>"`. **Blocks (exit 2)** on denied shell patterns. |
| `PreToolUse(Write\|Edit\|MultiEdit\|NotebookEdit)` | `enforce_policy_on_write.py` | Calls `policy_guard --action "write:<path>"`. **Blocks (exit 2)** on writes to `.env`, `.git/**`, `CLAUDE.md`, `policies/**`, `wiki/raw/**`. |
| `PostToolUse(Write\|Edit\|...)` | `karpathy_invariant_check.py` | Scans `memory/` for `.md` files. Soft warn (no block). |
| `Stop` | `suggest_epoch_learner.py` | If ≥ 20 invocations since last epoch, suggests running `epoch_learner`. |

### Disable temporarily

For legitimate tier-4 amendments (editing `CLAUDE.md` or `policies/**` under user authorization):

```bash
# Set env var before launching Claude Code — platform-specific:
export AGENTIC_OS_HOOKS_DISABLED=1    # bash/zsh
$env:AGENTIC_OS_HOOKS_DISABLED = "1"  # PowerShell
```

### Legitimate bypass route

For one-off tier-4 amendments without disabling the hook globally: use
`Bash + Python` to touch the file directly. The Bash hook checks shell patterns,
not file writes, so `python -c "open(...).write(...)"` goes through. **Always
log the amendment** in `memory/logs.json` with `outcome: "constitution_amendment"`
or `"policy_amendment"` so the bypass leaves an audit trail.

### Per-session override

Edit `.claude/settings.local.json` (not version-controlled) to disable a
specific matcher without touching the shared `settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [] }
    ]
  }
}
```

### What hooks complement

- `security.yaml` — the rule source (allowlist + denylist)
- `policy_guard.py` — the rule evaluator (pure, deterministic)
- **Hooks** — the enforcer at the Claude Code tool boundary (hard block)
- Per-agent `tools:` whitelist in `registry.json` — second line of defence
- `governance.yaml` tiers — HITL escalation for tier 3+ actions

Hooks block the clearly-wrong; tiers surface the uncertain for user review.

---

## 7 · Daily loop (TL;DR)

```
1. Ask the orchestrator agent to do the work.
2. End-of-day:     python .claude/core/epoch_learner.py --window 20
3. Weekly:         summary.py · forecast.py · consolidator.py --dry-run
4. Monthly:        consolidator.py --apply · test_runner.py
5. When curious:   graph_query --stats · scoring_engine --stats <agent>
```

---

## 8 · Escalation paths

| Situation | Escalation |
|-----------|------------|
| Circuit breaker trips (3× same failure) | Orchestrator emits `escalation` payload → user |
| Aggregate uncertainty ≥ 0.6 on high-stakes node | Orchestrator forks to `debate_moderator` → may still escalate |
| Evaluator verdict `retryable=false` | Log + user notification |
| `architecture_optimizer` proposes a change | Tier 4 — always user-approved |
| Constitution or policy amendment | Tier 4 — always user-approved, logged as `constitution_amendment` |
| `policy_guard` denies an action | Abort that node; log `policy_violation` |

---

## 9 · Where things live

```
.claude/
├── CLAUDE.md                 constitution (v5.0)
├── runtime.md                canonical loop
├── USAGE.md                  this file
├── commands/                 slash commands (/initialize)
├── agents/                   23 agents across 4 layers
│   ├── cognitive/            planner, reasoner, decomposer, debate_moderator,
│   │                         pattern_extractor, strategy_explorer
│   ├── execution/            code_agent, research_agent, tool_executor
│   ├── governance/           critic, security, evaluator, reflection,
│   │                         knowledge_validator
│   └── meta/                 orchestrator, factory, wiki_updater, wiki_curator,
│                             registry_manager, performance_optimizer,
│                             meta_controller, goal_keeper, architecture_optimizer
├── core/                     16 core modules
├── tools/                    CLI utilities + tool_registry.json
├── policies/                 security.yaml, config.yaml, governance.yaml,
│                             domain_policies.yaml, values.yaml
├── wiki/                     primary memory (7 knowledge domains + raw/)
│   ├── concepts/
│   ├── strategies/
│   ├── experience/
│   ├── goals/
│   ├── self/
│   ├── patterns/
│   ├── consensus/
│   ├── graph/graph.json      indexed knowledge graph
│   ├── raw/                  immutable ingestion input
│   ├── summaries/
│   ├── index.md              nav root (curated by wiki_curator)
│   └── registry.json         agent catalogue (23 agents)
├── memory/                   JSON-only transactional state (Karpathy invariant)
│   ├── logs.json
│   ├── agent_history.json
│   ├── trust_matrix.json
│   ├── goals_state.json
│   ├── system_profile.json
│   ├── world_state.json
│   ├── environment_state.json
│   ├── simulation_history.json
│   ├── forecasts.json
│   ├── consolidation_log.json
│   ├── budgets.json
│   └── corpus_df.json
├── observability/
│   ├── traces.json           append-only
│   └── summary.py            human-readable stats CLI
└── workflows/                pre-baked DAG templates
    ├── codegen_pipeline.json
    ├── debug_pipeline.json
    └── rag_pipeline.json
```
