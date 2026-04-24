# Sliding Window Rate Limiter (Case Study)

Production-grade sliding-window-counter rate limiter in pure Python. Zero deps.

## Public API

    from rate_limiter import RateLimiter

    rl = RateLimiter(limit=100, window_seconds=60.0, max_keys=100_000, key_ttl_seconds=3600.0)
    if rl.allow("user-123"):
        serve_request()
    else:
        return 429

    # async variant
    if await rl.allow_async("user-123"):
        ...

    # observability
    rl.stats("user-123")   # {"current_count", "previous_count", "estimated_rate"}
    rl.cardinality()        # live key-count

    # management
    rl.reset("user-123")    # clear one key
    rl.reset()              # clear all

## Guarantees

- Per-key isolation.
- Thread-safe (all structural ops under global lock + per-key lock for check-increment).
- ~1% approximation under boundary races (inherent to sliding-window-counter; use token-bucket if exact).
- Bounded memory via max_keys LRU eviction + key_ttl_seconds TTL sweep.
- Zero external deps (stdlib only + pytest for tests).

## Performance (Python 3.12, Windows)

| Scenario | Throughput |
|---|---|
| All-allow (no denial path) | 358k ops/sec |
| Mixed allow/deny (1k limit, 1M calls) | 366k ops/sec |
| Many keys (100 keys round-robin) | 369k ops/sec |

Target was 100k ops/sec; delivered ~3.5x.

## Tests

    py -3 -m pytest -q test_rate_limiter.py

40 tests: unit + concurrency (50 threads x 1000 ops) + adversarial burst + async + edge cases.

## Benchmark

    py -3 bench.py

## Build story

This limiter was built by the Agentic OS v5.5 government as an end-to-end test:

- Lead Agent (main session) dispatched 3 specialists in parallel: python-pro, test-automator, performance-engineer.
- Round-1 Council review (critic, evaluator, security) BLOCKED ship despite 40/40 tests and 422k ops/sec bench.
- Loop-back: worker fixed 3 HIGH findings (memory growth, dict-race, input validation).
- Round-2 Council: unanimous SHIP.
- Lead Agent independently verified (5 pytest runs + bench).

Full audit trail: see COUNCIL_VERDICT.md.

## Files

- rate_limiter.py     (313 lines, single module)
- test_rate_limiter.py (40 tests)
- bench.py
- SPEC.md             (acceptance criteria)
- COUNCIL_VERDICT.md  (full audit trail)
