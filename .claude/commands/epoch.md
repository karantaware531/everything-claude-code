# /epoch

Run the end-of-epoch learning cycle: update the self-model, generate forecasts, and review system health.

## When to Use
After ~20 agent invocations, at the end of a work day, or when the `suggest_epoch_learner` hook fires.

## Steps

1. **Run epoch_learner**:
   ```bash
   python .claude/core/epoch_learner.py --window 20
   ```
   Updates `memory/system_profile.json` with per-agent competence scores, weak spots, and strong pairings.
   Stages new `wiki/self/` narrative.

2. **Generate forecasts**:
   ```bash
   python .claude/core/forecast.py --metric success_rate --horizon 10
   python .claude/core/forecast.py --metric avg_reward --horizon 10
   ```
   Saves projections to `memory/forecasts.json`.

3. **Run observability summary**:
   ```bash
   python .claude/observability/summary.py
   ```
   Shows per-agent pass rate, latency, recent failures.

4. **Harness audit**:
   ```bash
   python .claude/tools/harness_audit.py
   ```
   7-category quality score. Flag any category below 6/10.

5. **Check forecasts** — if any metric is projected to cross alert threshold:
   - Invoke `performance_optimizer --mode global`
   - Review weak agents for amendment via `registry_manager`

6. **Consolidation check** (weekly):
   ```bash
   python .claude/core/consolidator.py --dry-run
   ```
   Review proposed merges and edge decays. Apply monthly with `--apply`.

7. **Compile self-narrative** (if epoch_learner produced new self-claims):
   ```bash
   python .claude/tools/wiki_compiler.py \
     --raw wiki/raw/docs/self-epoch-<N>.md \
     --domain self
   ```

8. **Report**:
   ```
   EPOCH: <N>
   SUCCESS RATE: <current> → <projected@+10>
   AVG REWARD:   <current> → <projected@+10>
   WEAK AGENTS:  <list>
   HARNESS SCORE: <overall>/10
   ACTION NEEDED: <list or "none">
   ```
