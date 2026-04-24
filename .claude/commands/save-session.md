# /save-session

Persist the current session state in a structured 8-section format for seamless continuation.

## When to Use
- Before ending a long session.
- Before context compaction (the precompact hook fires this automatically).
- Any time you want to guarantee continuity across sessions.
- Before switching branches or tasks mid-session.

## Output Location
`~/.claude/session-data/YYYY-MM-DD-<task-slug>-session.md`

## The 8-Section Format

### Section 1: What We Are Building
One paragraph: goal, current milestone, definition of done.

### Section 2: What WORKED (with evidence)
Bullet list of approaches that succeeded. Include:
- What specifically worked
- Why it worked (hypothesis)
- Confidence that it will work again

### Section 3: What Did NOT Work (MOST CRITICAL)
Bullet list of approaches that failed. For each:
- Exact failure description
- Root cause (not just symptom)
- Why retrying would fail the same way
- **This section is what saves future sessions from repeating past mistakes.**

### Section 4: What Has NOT Been Tried Yet
Bullet list of promising approaches not yet attempted. Priority-ordered.

### Section 5: Current State of Files
Table of relevant files and their current status:
```
| File | Status | Notes |
|---|---|---|
| src/auth.py | Complete | Tested, passes |
| src/api.py | In progress | Missing error handling |
```

### Section 6: Decisions Made
Bullet list of architectural/design decisions with rationale. No reversals without revisiting these.

### Section 7: Blockers and Open Questions
- Hard blockers (cannot proceed without resolving)
- Open questions (need research before deciding)

### Section 8: Exact Next Step
One sentence. Specific. Actionable. The first thing the next session should do.

## Steps

1. Review recent conversation and tool calls.
2. Write all 8 sections — prioritise Section 3 (failures) over all others.
3. Save to `~/.claude/session-data/YYYY-MM-DD-<task-slug>-session.md`.
4. Print the file path for the user.
5. Confirm: "Session saved. Resume with: /resume-session <slug>"
