---
domain: concepts
slug: agent-frontmatter-distribution
first_observed: 2026-04-24T00:00:00Z
last_updated: 2026-04-24T00:00:00Z
confidence: 0.95
task_id: v5.5-frontmatter-decision
---

# Agent Frontmatter Distribution — Decision Table (user-facing)

Per-agent reasoning for every canonical field. Read this, decide per agent if you
want to override. Override by editing the `.claude/agents/<layer>/<name>.md` frontmatter.

## Field reference

| Field | Purpose | Values |
|---|---|---|
| `model` | Cost/capability tradeoff | `haiku` (cheap, fast), `sonnet` (balanced), `opus` (deep reasoning) |
| `memory` | Cross-session persistence | `project` (`.claude/agent-memory/<name>/` — team-shared), `user` (`~/.claude/agent-memory/<name>/` — personal), `local` (gitignored) |
| `color` | UI distinguisher in task lists | red/orange/yellow/green/blue/cyan/magenta/purple |
| `maxTurns` | Runaway cap (self-dialog turns) | integer; low for deterministic, high for deliberative |
| `tools` | Explicit allowlist | `Read, Grep, Glob` (read-only), + `Write, Edit, Bash` (workers) |
| `disallowedTools` | Explicit denylist | Use for governance to hard-block Write/Edit |
| `permissionMode` | Per-agent override | Usually inherit; `plan` for read-only roles |
| `isolation` | Worktree isolation | `worktree` for risky parallel edits |

## Layer color scheme

Colors encode role semantic — change if conflicts with personal preference.

- **red / orange / yellow / purple** → governance (severity signal)
- **magenta** → meta / control plane
- **blue / cyan** → cognitive / deliberative
- **green** → execution / workers

---

## Cognitive Layer (6)

### planner
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | opus | DAG generation benefits from deep reasoning; one-shot high-stakes | sonnet if latency-sensitive |
| memory | project | Learns winning DAG shapes across tasks; shared across team | user if you want personal planning style |
| color | blue | Deliberative family | — |
| maxTurns | 20 | Planning loops can need multiple DAG revisions | 10 if you want stricter cap |
| tools | Read, Grep, Glob, Bash | Reads strategies, runs simulations | add Write if planner should save draft plans |

### reasoner
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Disambiguation is not that complex; sonnet suffices | haiku to save cost, opus if ambiguous-goal failures mount |
| memory | project | Learns which disambiguations are typical for this project | — |
| color | cyan | Cognitive secondary | — |
| maxTurns | 10 | Disambiguation rarely needs > 5 turns | 5 if aggressive |

### decomposer
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Splitting tasks is structural, not creative | haiku if tasks are simple/repetitive |
| memory | project | Learns how composite tasks typically split | — |
| color | cyan | Cognitive secondary | — |
| maxTurns | 10 | Decomposition is finite | 5 if aggressive |

### strategy_explorer
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | opus | Generates K candidate DAGs + utility scoring — high stakes | sonnet if exploration is infrequent |
| memory | project | Accumulates winning exploration patterns | — |
| color | blue | Deliberative | — |
| maxTurns | 25 | K=3 candidates × 8 turns each = ~24 | 15 if K is smaller |

### debate_moderator
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | opus | Adjudication between conflicting claims; needs strong reasoning | sonnet if debates are simple |
| memory | project | Consensus compounds across sessions (`.claude/notes/consensus/`) | — |
| color | blue | Deliberative | — |
| maxTurns | 20 | 2-round cap × ~10 turns + council synthesis | 15 if cost-sensitive |

### pattern_extractor
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Pattern mining is structural | haiku if patterns are simple substring matches |
| memory | project | Learns pattern registry over time | — |
| color | cyan | Cognitive secondary | — |
| maxTurns | 15 | Scanning + emitting markdown | 10 if few strategies |

---

## Execution Layer (4)

### code_agent
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Bulk of coding tasks; upgrade specific tasks via voltagent-lang specialists | opus for hardest bugs, haiku never (too weak for real code) |
| memory | project | Learns project's coding conventions | user if you want personal style to transfer |
| color | green | Worker | — |
| maxTurns | 30 | Long coding sessions need headroom | 20 if you keep tasks small |
| tools | default (Read, Write, Edit, Bash, Grep, Glob) | Full toolkit | — |
| isolation | worktree | Prevents corrupting main branch on risky changes | remove if you trust it on trunk |

### research_agent
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | haiku | Research is read-heavy; haiku + parallel subagents > opus alone | sonnet if research produces poor summaries |
| memory | project | Learns which sources are authoritative for the project | — |
| color | green | Worker | — |
| maxTurns | 15 | Web+repo scan + summarize | 25 for deep research tasks |

### tool_executor
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | haiku | Just invokes registered tools per protocol | — |
| memory | local | Session-scoped; tool outputs are transient | project if you want tool trace persistence |
| color | green | Worker | — |
| maxTurns | 10 | One-shot tool calls | 5 if strict |

### graphify_agent
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | haiku | Wraps CLI; minimal reasoning | sonnet if Q&A interpretation becomes important |
| memory | project | Accumulates query-answer feedback loop (`save-result`) | — |
| color | green | Worker | — |
| maxTurns | 10 | CLI wrapper | — |

---

## Governance Council (5) — VETO on ship

### critic
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | **opus** | First quality gate; must catch subtle issues | sonnet only if you are cost-critical and accept lower catch-rate |
| memory | project | Builds catalog of common flaws seen in this project | — |
| color | **red** | Signals block/critical role | — |
| maxTurns | 15 | Multiple passes on tricky outputs | 10 if strict |
| tools | Read, Grep, Glob | Read-only — must not write to enforce review integrity | — |

### evaluator
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Structural grading; rubric-based | opus if eval outputs are unreliable |
| memory | project | Learns accuracy of its own uncertainty estimates over time | — |
| color | orange | High-severity gate | — |
| maxTurns | 10 | Finite checklist | 5 if strict |
| tools | Read, Grep, Glob, Bash | Runs test scripts | — |

### security
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | **opus** | Novel threat reasoning; false negatives are catastrophic | never downgrade below sonnet |
| memory | project | Learns project's threat surface (auth boundaries, data flows) | — |
| color | **red** | Blocks on critical | — |
| maxTurns | 15 | Cross-file attack-trace analysis | — |
| tools | Read, Grep, Glob, Bash | Read + run security scanners | — |

### reflection
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | opus | Strategy synthesis + prompt-amendment proposals require depth | sonnet if outputs are verbose |
| memory | project | Writes strategies/experience to `.claude/notes/` — that IS the memory | — |
| color | purple | Reflective / meta | — |
| maxTurns | 20 | Longer post-task analysis | 10 if fast cycles |
| tools | Read, Write, Edit, Bash, Grep, Glob | Writes to notes/; triggers graphify | — |

### knowledge_validator
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Deterministic scoring (authority / freshness / trials) | opus overkill |
| memory | project | Tracks resolved contradictions | — |
| color | yellow | Caution/evaluative signal | — |
| maxTurns | 10 | Scoring is bounded | 5 if strict |
| tools | Read, Grep, Glob, Bash | Read notes/ + run scoring | — |

---

## Meta Layer (6 — orchestrator retired in v5.5; Lead Agent = main session)

### factory
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | opus | Spec generation + validation pipeline is critical | sonnet if new agents are rare |
| memory | project | Learns which capability gaps keep recurring | — |
| color | magenta | Control plane | — |
| maxTurns | 12 | Spec → validate → register pipeline | 8 if strict |

### registry_manager
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Validator + bookkeeper; no creative work | — |
| memory | project | Catalog of amendment history | — |
| color | magenta | Control plane | — |
| maxTurns | 8 | Short by design | — |

### performance_optimizer
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Aggregates stats + proposes fixes | opus for complex merge decisions |
| memory | project | Tracks weak agents over time | — |
| color | magenta | Control plane | — |
| maxTurns | 15 | Weekly runs; multi-agent analysis | — |

### meta_controller
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Tier computation is rule-based | — |
| memory | project | Learns domain failure patterns → tier bumps | — |
| color | magenta | Control plane | — |
| maxTurns | 8 | Fast decision | — |

### goal_keeper
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | sonnet | Goal tracking + drift detection | — |
| memory | project | Long-term goals live here | — |
| color | magenta | Control plane | — |
| maxTurns | 8 | Short update cycles | — |

### architecture_optimizer
| Field | Current | Why | Alternatives |
|---|---|---|---|
| model | **opus** | Structural proposals are tier 4 always; must be best reasoning | never downgrade |
| memory | project | Tracks structural history + rollback plans | — |
| color | magenta | Control plane | — |
| maxTurns | 20 | Deep analysis + rollback plan | — |

---

## Override guide

To change any field for any agent, edit the frontmatter directly:

```yaml
---
name: code_agent
model: opus       # was sonnet; upgrade for harder tasks
memory: user      # was project; personalize to you
color: purple     # was green; your choice
maxTurns: 40      # was 30; longer runway
---
```

The frontmatter file is single source of truth. No regeneration needed.

## When to reconsider

| Signal | Which field to revisit |
|---|---|
| Agent running out of turns mid-task | `maxTurns` too low |
| Agent giving shallow outputs | `model` too weak (upgrade to sonnet/opus) |
| Agent outputs generic (not project-aware) | `memory` should be `project` |
| Two agents indistinguishable in logs | `color` — assign unique |
| Workers modifying files they should not | add `disallowedTools` or tighten `tools` |
| Code agent breaking main branch | add `isolation: worktree` |
| Governance agent writing to files | add `disallowedTools: Write, Edit` |

---

## Default policy

Unless you override: keep v5.5 defaults (this doc). They are cost-balanced for
a mid-size project with moderate task volume. Review at every epoch boundary
(`/epoch` command) and adjust based on `scoring_engine` weak-spot findings.
