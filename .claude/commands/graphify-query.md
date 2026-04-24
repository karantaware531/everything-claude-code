# /graphify-query

Shortcut: BFS/DFS traversal query against the unified knowledge graph.

## Usage

```
/graphify-query "what strategies worked for debug tasks?"
/graphify-query "how does reflection reach planner?" --dfs
/graphify-query "find contradictions in goal_keeper" --budget 1500
```

## Steps

1. Verify `graphify-out/graph.json` exists. If missing, tell the user to run `/graphify-build` first.
2. Call the Graphify CLI:
   ```bash
   py -3 -m graphify query "<question>" [--dfs] [--budget N]
   ```
3. Read the returned subgraph (nodes + edges + confidence tags + source locations).
4. Answer using ONLY what the graph contains. Quote `source_location` for citations.
5. If the graph lacks information, say so explicitly — do not invent edges.
6. Save the Q&A back into the graph:
   ```bash
   py -3 -m graphify save-result --question "<Q>" --answer "<A>" --type query --nodes <N1> <N2>
   ```

## Modes

| Flag | When to use |
|---|---|
| _(none — default BFS)_ | "What is X connected to?" — broad context, nearest neighbours |
| `--dfs` | "How does X reach Y?" — trace a specific chain or dependency |
| `--budget N` | Cap answer at N tokens (default 2000) |

## See also

`.claude/commands/graphify.md` (full skill with all subcommands),
`.claude/agents/execution/graphify_agent.md`.
