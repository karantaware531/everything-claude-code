---
paths:
  - "**/*.py"
  - "**/*.js"
  - "**/*.ts"
  - "**/*.jsx"
  - "**/*.tsx"
  - ".github/workflows/*.yml"
  - ".github/workflows/*.yaml"
---

# Security-Pattern Rules (enforced by security_reminder_hook.py at Write/Edit)

The PreToolUse security hook **blocks** writes containing any of these patterns.
First occurrence per file per session gets a warning + block; fix or justify, then proceed.

## Blocked patterns (summary)

| Pattern class | Risk | Safe alternative |
|---|---|---|
| Dynamic code eval (JS `eval`, `new Function`, Python `exec`) | Arbitrary code execution | `JSON.parse()` for data, redesign for code |
| Shell via Node child_process | Shell injection | `execFile` with arg array |
| React `dangerouslySetInnerHTML` | XSS | `textContent` or DOMPurify-sanitized HTML |
| DOM `.innerHTML =`, `document.write` | XSS + perf | `textContent`, `createElement` + `appendChild` |
| Python `pickle` | Deserialization RCE | `json`, `msgpack`, explicit schema |
| Python `os.system` | Shell injection | `subprocess.run([...], shell=False)` |
| GitHub Actions `${{ github.event.* }}` in `run:` | Workflow injection | `env:` block + `"$VAR"` quoting |

Full pattern strings live in `.claude/hooks/security_reminder_hook.py` (SECURITY_PATTERNS list).

## Discipline for LEGITIMATE uses

If you genuinely need one of these patterns (rare):
1. Justify in code comment explaining why the safer alternative does not fit.
2. Add input validation / sanitization immediately adjacent.
3. Route the change through `/review` — `critic` + `security` agents must explicitly approve.
4. The hook will still fire once per file per session; that is expected. It is a speedbump, not a fence.

## Disabling (for legitimate amendments)

Per-session: `ENABLE_SECURITY_REMINDER=0` (plugin's own switch).
Global: `AGENTIC_OS_HOOKS_DISABLED=1` (all our hooks).

Both are auditable via `memory/logs.json` ConfigChange events.
