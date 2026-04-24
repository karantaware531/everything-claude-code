# /graphify-build

Shortcut: full Graphify pipeline over the whole project (code + `.claude/notes/`).

Defer to the complete pipeline in `.claude/commands/graphify.md` (or the global
`graphify` skill). This shortcut just invokes the right default target.

## Usage

```
/graphify-build                    # build from repo root (default)
/graphify-build .claude/notes/     # just the narrative notes
/graphify-build --mode deep        # aggressive inference
/graphify-build --directed         # preserve edge direction
```

## Steps

1. Invoke the full `/graphify` pipeline with target `.` (repo root).
2. Wait for completion — outputs to `graphify-out/graph.json`, `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`.
3. Report back: node count, edge count, community count, god nodes, top surprising connections.
4. Offer to explore the most interesting suggested question.

## After-build actions

- If `graphify-out/GRAPH_REPORT.md` exists, relay the **God Nodes**, **Surprising Connections**, and **Suggested Questions** sections (only those three) to the user.
- Offer one follow-up query: "The most interesting question this graph can answer: **<Q>**. Want me to trace it?"

## See also

- `.claude/commands/graphify.md` — full pipeline with all flags and options
- `.claude/agents/execution/graphify_agent.md` — programmatic access from other agents
- `.claude/notes/README.md` — what Graphify indexes and why
