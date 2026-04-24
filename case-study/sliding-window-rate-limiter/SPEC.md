# Case Study — Sliding Window Rate Limiter

**Agentic OS v5.5 Government Stress Test** (2026-04-24)

This folder is the unmodified output of a single-session test: the Lead Agent
(main Claude Code session) dispatched the task to domain specialists via the
Task tool, routed the result through the Consensus Council, and verified with
real `pytest` runs. No human in the loop for implementation decisions.

## The task (chosen because real libraries still struggle with it)

Production-grade **sliding-window-counter rate limiter** in pure Python.

## Acceptance criteria (objective, verifiable)

1. **Correctness**: Sliding-window-counter algorithm (weighted). Per-key isolation. Given N req/window of W seconds, `allow(key)` returns True at most N times within any W-second interval.
2. **Thread safety**: 50 threads × 1000 ops (50k total) — no over-allow, no lost updates.
3. **Async support**: `async def allow_async(key)` with same semantics, non-blocking.
4. **Performance**: ≥ 100,000 ops/sec single-threaded, stdlib only.
5. **Tests**: unit + concurrency + adversarial burst. `python -m pytest` all green.
6. **Zero external deps** (stdlib + pytest).

## Algorithm (sliding window counter, weighted)

```
current_window  = floor(now / W)
previous_window = current_window - 1
elapsed_frac    = (now % W) / W
weight_prev     = 1.0 - elapsed_frac
estimated_rate  = counts[K][current] + counts[K][previous] * weight_prev
if estimated_rate < N:
    counts[K][current] += 1
    return True
return False
```

## Deliverables

- `rate_limiter.py` — module
- `test_rate_limiter.py` — pytest suite
- `bench.py` — throughput benchmark
- `README.md` — usage
- `COUNCIL_VERDICT.md` — critic + evaluator + security verdict

## Government flow (what this exercises)

```
Lead Agent (main session)
  │
  ├──▶ voltagent-lang:python-pro        (implementation)
  ├──▶ voltagent-qa-sec:test-automator  (test suite)
  ├──▶ voltagent-qa-sec:performance-engineer  (benchmark)
  │
  ▼
Consensus Council
  ├──▶ critic      (red-team findings; opus)
  ├──▶ evaluator   (correctness + completeness; sonnet)
  └──▶ security    (injection/race/overflow review; opus)
  │
  ▼
Verify via pytest + bench on real host Python
```

Unanimous Council verdict required before this case-study ships.
