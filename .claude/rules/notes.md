---
paths:
  - ".claude/notes/**/*.md"
---

# Notes Write Discipline (v5.2 Graphify era)

## Required frontmatter
```yaml
---
domain: concepts|strategies|experience|goals|self|patterns|consensus
slug: kebab-case-unique-identifier
first_observed: <ISO-8601 timestamp>
last_updated: <ISO-8601 timestamp>
confidence: <float 0.0-1.0>
---
```

## Optional frontmatter
- `task_id` — session task that produced this note
- `agents` — list of contributing agents
- `supersedes` — list of slugs this replaces
- `source` — URL/path for externally-derived content

## Write rules
1. **One concept per file.** Update in place when revisiting; Graphify's SHA256 cache handles re-indexing.
2. **Link via `[[wiki-links]]`.** Graphify's semantic extractor turns these into graph edges.
3. **Never include secrets/tokens/PII.** These files get indexed into `graphify-out/graph.json` (committed).
4. **Cite sources** with inline URL or `source:` frontmatter. AMBIGUOUS edges flag unverified claims.
5. **Domain discipline**: strategies = what worked; experience = what we learned; goals = long-term direction; self = system's self-model; patterns = cross-task abstractions; consensus = persistent debate outcomes; concepts = general knowledge.

## After every write
Trigger incremental graph update:
```bash
py -3 -m graphify .claude/notes/ --update
```
Or hand off to `graphify_agent` with `action=update`. Writer agents do this automatically.
