"""Benchmark: sliding-window-rate-limiter — single-threaded throughput."""

import sys
import time

sys.path.insert(0, ".")
from rate_limiter import RateLimiter

TARGET = 100_000  # ops/sec minimum


def run(name: str, rl: RateLimiter, calls: int, keys: list) -> float:
    key_count = len(keys)
    t0 = time.perf_counter()
    for i in range(calls):
        rl.allow(keys[i % key_count])
    elapsed = time.perf_counter() - t0
    ops = calls / elapsed
    ns = elapsed * 1e9 / calls
    print(f"{name}: calls={calls} elapsed={elapsed:.3f}s ops/sec={ops:,.0f} ns/op={ns:.1f}")
    return ops


def main() -> None:
    results = []

    # Scenario 1 — all-allow (limit so high it never fires)
    rl1 = RateLimiter(limit=10_000_000, window_seconds=60)
    results.append(run("all-allow   ", rl1, 1_000_000, ["key"]))

    # Scenario 2 — mixed allow/deny (limit=1000/s, 1M calls -> most denied)
    rl2 = RateLimiter(limit=1_000, window_seconds=1)
    results.append(run("mixed       ", rl2, 1_000_000, ["key"]))

    # Scenario 3 — many keys round-robin (100 keys, limit=100 each)
    keys100 = [f"k{i}" for i in range(100)]
    rl3 = RateLimiter(limit=100, window_seconds=1)
    results.append(run("many-keys   ", rl3, 1_000_000, keys100))

    verdict = "BENCH_PASS" if all(r >= TARGET for r in results) else "BENCH_FAIL"
    print(verdict)


if __name__ == "__main__":
    main()
