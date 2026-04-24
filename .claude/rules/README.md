# .claude/rules/ — Path-Scoped Rules (v5.4)

Rules fire based on `paths:` YAML frontmatter. Claude Code loads a rule only
when the current task touches a file matching one of its paths. This keeps
CLAUDE.md lean and focused; domain-specific guidelines live here.

Format:
```yaml
---
paths:
  - "src/api/**/*.ts"    # glob patterns
  - "tests/**/*.py"
---
# Rule content...
```

Without `paths:`, a rule is global (loads every session — avoid unless truly universal).

## Current rules

| File | Scope | Purpose |
|---|---|---|
| `agents.md` | `.claude/agents/**` | Agent markdown file conventions |
| `hooks.md` | `.claude/hooks/**` | Hook script contract (exit codes, stdin/stdout) |
| `notes.md` | `.claude/notes/**` | Narrative note frontmatter + write discipline |
| `testing.md` | `**/*.test.py`, `**/*_test.py` | Python test conventions |

Add new rules freely. Ephemeral rules belong in `.claude/settings.local.json`
instead (not committed).
