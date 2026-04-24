# /council

Run a 4-voice adversarial decision framework for hard architectural or strategic choices.

## When to Use
- Binary/trinary forks: monorepo vs polyrepo, ship-now vs polish-first, rewrite vs refactor.
- Technology choices with significant long-term consequences.
- Any decision where anchoring bias could corrupt the outcome.

## When NOT to Use
- Implementation planning (use planner).
- Code review (use /review).
- Factual questions (use research_agent).
- Bug diagnosis (use /debug).

## Anti-Anchoring Design
Each advisor subagent receives ONLY the decision question and minimal relevant context.
NO conversation history. NO prior agent opinions.
This eliminates anchoring bias — the primary failure mode of sequential consultation.

## Steps

1. **State the decision** — frame as: "Should we [A] or [B]? Context: [minimal facts]."

2. **Spawn 4 independent subagents** (each with isolated context — no shared history):

   | Advisor | Lens | Bias |
   |---|---|---|
   | **Architect** | Long-term correctness, maintainability, scaling | Conservative |
   | **Skeptic** | Assumption-breaking, what could go wrong | Pessimistic |
   | **Pragmatist** | Shipping speed, simplicity, what works now | Optimistic |
   | **Critic** | Edge cases, blind spots, hidden costs | Analytical |

3. **Collect 4 independent verdicts** — each advisor states:
   - Their recommendation
   - Their top 3 reasons
   - Their biggest concern with the alternative

4. **Synthesize** — display all 4 positions before drawing conclusions:
   - Where do advisors converge? (strong signal)
   - Where do they diverge? (uncertainty signal)
   - Does any advisor surface a concern the others missed?

5. **Reach verdict** — synthesise a final recommendation:
   - If 3+ advisors agree → proceed with confidence
   - If 2-2 split → examine Skeptic and Architect positions most carefully
   - If all 4 disagree → escalate to debate_moderator

6. **Persist decision** (if it changes something real):
   - Write to `wiki/consensus/<decision-slug>.md`
   - Include: decision, verdict, rationale, reopen conditions
   - Debate_moderator will check here first next time this topic arises

## Output Format
```
COUNCIL DECISION: <topic>

ARCHITECT: [A|B] — <top reason>
SKEPTIC:   [A|B] — <top concern>
PRAGMATIST:[A|B] — <top reason>
CRITIC:    [A|B] — <top concern>

CONVERGENCE: <A=N, B=M> advisors
FINAL VERDICT: [A|B|ESCALATE]
RATIONALE: <2-3 sentences>
PERSIST: [YES — wiki/consensus/<slug>.md | NO — not a lasting decision]
```
