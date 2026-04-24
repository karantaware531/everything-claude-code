# Post-Refresh Validation Checklist

After `/graphify-refresh` completes:

- [ ] `graphify-out/graph.json` mtime is newer than command start.
- [ ] `graphify-out/cost.json` incremented `runs` count.
- [ ] No errors in `graphify-out/.graphify_detect.json` (should be absent after cleanup).
- [ ] If AMBIGUOUS edges added → flag for `knowledge_validator`.
- [ ] If god-node rank shifted → `pattern_extractor` may want to re-scan.
- [ ] Log the refresh in `memory/logs.json` with `outcome: "graph_refresh"`.
