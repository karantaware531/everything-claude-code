# /explore

Generate K candidate execution strategies for a high-stakes task, simulate each, and pick the best by expected utility.

## When to Use
- High-stakes tasks where the wrong plan is costly (tier ≥ 3).
- When you're uncertain which agent sequence will work best.
- When task_type has `strategy_exploration: true` in `policies/config.yaml`.
- Explicitly: any time you want deliberative planning instead of reactive planning.

## When NOT to Use
- Routine, well-understood tasks (adds K simulation overhead).
- Tasks where you already have a winning strategy in `wiki/strategies/`.

## Steps

1. **Receive task description** — the more specific, the better the candidates.

2. **Check wiki/strategies/** — if a matching strategy exists with high confidence, return it directly. No need for exploration.

3. **Invoke strategy_explorer** agent with:
   - Task context
   - k=3 (default; override with `--k <N>`)
   - Current autonomy tier

4. **strategy_generator produces K candidates** by varying:
   - Agent assignments (swap alternates via semantic similarity)
   - Decomposition depth (coarse vs fine-grained)
   - Execution structure (sequential vs parallel where DAG allows)

5. **Simulate each candidate** via `execution_engine --simulate`:
   - Risk report per candidate
   - Estimated token cost per candidate
   - Predicted success probability

6. **Score by expected utility**:
   ```
   EU = p_success × reward − (1 − p_success) × risk_cost
   ```
   Rank candidates by EU. Flag if EU < 0 across all paths (→ escalate tier).

7. **Return best candidate** to orchestrator / planner as the recommended DAG.

8. **Log exploration** to `observability/traces.json`:
   - All K candidates with their EU scores
   - Winning candidate + rationale
   - Discarded candidates + reasons

## Output Format
```
EXPLORATION COMPLETE: <task slug>
CANDIDATES GENERATED: <K>
WINNER: candidate-<N> (EU=<score>)
  Agents: <sequence>
  Risk: <low|medium|high>
  Est. tokens: <N>
RUNNER-UP: candidate-<M> (EU=<score>)
DISCARDED: <N-2 candidates with reasons>
```
