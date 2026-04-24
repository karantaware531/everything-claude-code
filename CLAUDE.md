# Project Instructions

@.claude/CLAUDE.md

---

## Quick Navigation

| What you need | Where it lives |
|---|---|
| System constitution (full rules) | `.claude/CLAUDE.md` |
| All agents & when to use them | `AGENTS.md` |
| Global coding rules | `RULES.md` |
| Operator's guide (usage, maintenance) | `.claude/USAGE.md` |
| Slash commands | `.claude/commands/` |
| MCP server config | `.mcp.json` |
| Knowledge wiki | `.claude/wiki/` |
| Core engine modules | `.claude/core/` |

## Project-Specific Notes

<!-- Add any project-specific overrides or context here.
     The full Agentic OS v5 constitution is in .claude/CLAUDE.md.
     This file is the Claude Code entry point — it @-includes the constitution. -->

## First Time Setup

```bash
# 1. Verify system health (expect 33/33 PASS)
python .claude/tools/test_runner.py

# 2. Run harness audit (expect >= 7/10 overall)
python .claude/tools/harness_audit.py

# 3. Initialize project context
# Use slash command: /initialize
```
