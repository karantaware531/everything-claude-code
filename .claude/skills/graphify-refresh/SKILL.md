---
name: graphify-refresh
description: Incrementally refresh graphify-out/graph.json after writes to .claude/notes/. SHA256-cached, only re-extracts changed files. Use after any narrative-writer agent (reflection, goal_keeper, pattern_extractor, debate_moderator, epoch_learner) writes markdown to .claude/notes/.
license: MIT
compatibility: Requires Graphify CLI (`py -3 -m graphify update`) available on PATH
metadata:
  project: agentic-os
  version: "5.7"
  argument_hint: "optional path; defaults to .claude/notes/"
---

# Graphify Refresh

Reference skill demonstrating `.claude/skills/` layout. Use this after any
narrative-writer agent (reflection, goal_keeper, pattern_extractor,
debate_moderator, epoch_learner) writes a markdown file to `.claude/notes/`.

## Steps

1. Determine target path:
   - If `$ARGUMENTS` given, use that path.
   - Otherwise default to `.claude/notes/`.

2. Run incremental update:
   ```bash
   py -3 -m graphify "$ARGUMENTS" --update
   ```

3. Verify output:
   - Check `graphify-out/graph.json` was updated (mtime newer than 10 seconds ago).
   - Check `graphify-out/cost.json` for token usage.

4. Report:
   - Delta node/edge counts vs previous run.
   - Any new AMBIGUOUS edges (candidates for `knowledge_validator`).

## Supporting files

See [checklist.md](checklist.md) for the post-refresh validation checklist.
