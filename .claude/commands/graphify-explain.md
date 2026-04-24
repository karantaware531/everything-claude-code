# /graphify-explain

Shortcut: plain-language explanation of a single node — what it is, what it connects to, why the connections matter.

## Usage

```
/graphify-explain "reflection"
/graphify-explain "debug-python-error-strategy"
/graphify-explain "code_agent"
```

## Steps

1. Verify `graphify-out/graph.json` exists. If missing, tell the user to run `/graphify-build` first.
2. Call:
   ```bash
   py -3 -m graphify explain "<node label>"
   ```
3. Read the node's attributes, connections, confidence tags.
4. Write a 3-5 sentence explanation:
   - What this node IS (its role/purpose)
   - What it connects to (top 3-5 neighbours by degree or relevance)
   - Why those connections are significant
5. Cite `source_file:source_location` for every factual claim.
6. Save the explanation back:
   ```bash
   py -3 -m graphify save-result --question "Explain <node>" --answer "<A>" --type explain --nodes <node>
   ```

## See also

`.claude/commands/graphify.md`, `.claude/agents/execution/graphify_agent.md`.
