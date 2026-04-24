# /graphify-path

Shortcut: shortest path between two concepts in the graph.

## Usage

```
/graphify-path "reflection" "planner"
/graphify-path "code_agent" "graphify_agent"
/graphify-path "debug-strategy" "evaluator"
```

## Steps

1. Verify `graphify-out/graph.json` exists. If missing, tell the user to run `/graphify-build` first.
2. Call:
   ```bash
   py -3 -m graphify path "<A>" "<B>"
   ```
3. Read the returned path: ordered list of nodes + relations + confidence tags.
4. Explain the path in plain language:
   - What each hop represents
   - Why the sequence matters (what flows through it)
   - Any AMBIGUOUS edges that weaken the connection
5. Save the path explanation back:
   ```bash
   py -3 -m graphify save-result --question "Path from <A> to <B>" --answer "<A>" --type path_query --nodes <A> <B>
   ```

## When there's no path

If `graphify path` returns "No path found", it means the two concepts live in
disconnected subgraphs — this is a signal to investigate whether they should be
linked (new relation in `.claude/notes/`) or whether the disconnection is
genuine structural information.

## See also

`.claude/commands/graphify.md`, `.claude/agents/execution/graphify_agent.md`.
