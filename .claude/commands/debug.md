# /debug

Diagnose and fix a bug, error, or unexpected behaviour using the evidence-first approach.

## When to Use
Any time you have an error message, unexpected output, failing test, or system misbehaviour.

## Philosophy
"Gather evidence first, patch second." Guessing without evidence produces patches that mask rather than fix. The GateGuard principle: investigation creates context that self-evaluation never did.

## Steps

1. **Capture failure** — document precisely:
   - Full error message + stack trace (paste verbatim)
   - Tool sequence that triggered it
   - Expected vs. actual behaviour
   - When it started (last known-good state)

2. **Research phase** — invoke `research_agent` to:
   - Read the file(s) mentioned in the stack trace
   - Read all callers of the failing function
   - Search for similar patterns in `wiki/experience/` (past lessons)
   - Search for prior bug fixes in `wiki/strategies/`

3. **Root cause diagnosis** — classify the failure pattern:
   | Pattern | Signature |
   |---|---|
   | Logic error | Wrong condition, off-by-one, missing null check |
   | Type mismatch | Unexpected type at boundary |
   | State corruption | Shared mutable state modified by concurrent path |
   | Missing dependency | Import error, missing file, unregistered tool |
   | Context pressure | Claude truncated; check token budget |
   | Race condition | Intermittent; order-dependent |

4. **Hypothesis → Minimal test** — before patching:
   - Write the smallest possible reproducer
   - Confirm it fails consistently
   - Document the exact line causing the failure

5. **Patch** — invoke `code_agent` with:
   - The root cause (not just the symptom)
   - The minimal reproducer
   - The expected fix
   - Any related code that must change simultaneously

6. **Verify** — run `/verify` to confirm fix:
   - Target test passes
   - No regressions in related tests
   - Build succeeds

7. **Reflect** — if this bug reveals a systemic pattern, invoke `reflection`:
   - Write an experience entry to `wiki/experience/`
   - Update any related concept in `wiki/concepts/`

## Output Format
```
ROOT CAUSE: <one-sentence diagnosis>
FIX APPLIED: <file:line — what changed>
REPRODUCER: <minimal test case>
VERIFY: [PASS | FAIL] <test name>
LESSONS LEARNED: <wiki/experience entry slug or "none">
```
