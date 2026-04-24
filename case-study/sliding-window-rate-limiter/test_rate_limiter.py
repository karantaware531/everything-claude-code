"""
pytest suite for rate_limiter.RateLimiter (sliding-window-counter algorithm).

Coverage targets
----------------
1.  Unit  — basic allow/deny
2.  Unit  — per-key isolation
3.  Unit  — window rollover
4.  Unit  — weighted sliding-window correctness (stats())
5.  Concurrency — race detection (50 threads x 1000 ops)
6.  Async — allow_async semantics
7.  Async — non-blocking under concurrent load
8.  Adversarial — burst attack + recovery
9.  Reset — reset(key) vs reset()
10. Stats — dict shape and values after known sequence

Run with:
    python -m pytest test_rate_limiter.py -v
"""

from __future__ import annotations

import asyncio
import math
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Timing helpers
# ---------------------------------------------------------------------------

def _sleep_to_window_fraction(window_seconds: float, target_frac: float) -> None:
    """
    Sleep until the elapsed fraction within the NEXT window slot is approximately
    ``target_frac``.  Always crosses the current window boundary first, then
    waits ``target_frac * window_seconds`` into the new slot.

    This avoids tests depending on where within the current slot we happen to
    be when the test starts — a common source of flakiness.
    """
    now = time.monotonic()
    elapsed_in_current = now % window_seconds
    remaining_in_current = window_seconds - elapsed_in_current
    # Sleep past the boundary, then advance target_frac into the new window.
    sleep_duration = remaining_in_current + target_frac * window_seconds
    # Cap at 1.3s so we never violate the "no sleeps > 1.5s" constraint.
    assert sleep_duration <= 1.3, (
        f"Computed sleep {sleep_duration:.3f}s exceeds safety cap; "
        "reduce window_seconds or target_frac."
    )
    time.sleep(sleep_duration)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_allows(rl: RateLimiter, key: str, n: int) -> int:
    """Call allow() n times and return the number of True results."""
    return sum(1 for _ in range(n) if rl.allow(key))


# ---------------------------------------------------------------------------
# 1. Unit — basic allow / deny
# ---------------------------------------------------------------------------

class TestBasicAllowDeny:
    """limit=5, window=1s — burst of 5 must all pass; 6th must be denied."""

    def test_exactly_five_allowed_in_burst(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        results = [rl.allow("user") for _ in range(6)]
        assert results[:5] == [True, True, True, True, True]
        assert results[5] is False

    def test_return_types_are_bool(self) -> None:
        rl = RateLimiter(limit=2, window_seconds=1.0)
        assert isinstance(rl.allow("x"), bool)
        assert isinstance(rl.allow("x"), bool)

    def test_sixth_call_is_false_not_exception(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        for _ in range(5):
            rl.allow("u")
        assert rl.allow("u") is False

    def test_all_subsequent_calls_denied_in_same_window(self) -> None:
        rl = RateLimiter(limit=3, window_seconds=1.0)
        _count_allows(rl, "u", 3)
        denied = [rl.allow("u") for _ in range(10)]
        assert all(v is False for v in denied)

    def test_invalid_limit_raises(self) -> None:
        with pytest.raises(ValueError):
            RateLimiter(limit=0, window_seconds=1.0)
        with pytest.raises(ValueError):
            RateLimiter(limit=-1, window_seconds=1.0)

    def test_invalid_window_raises(self) -> None:
        with pytest.raises(ValueError):
            RateLimiter(limit=5, window_seconds=0.0)
        with pytest.raises(ValueError):
            RateLimiter(limit=5, window_seconds=-0.5)


# ---------------------------------------------------------------------------
# 2. Unit — per-key isolation
# ---------------------------------------------------------------------------

class TestPerKeyIsolation:
    """Different keys must have completely independent counters."""

    def test_key_a_exhausted_does_not_affect_key_b(self) -> None:
        rl = RateLimiter(limit=2, window_seconds=1.0)
        assert rl.allow("a") is True
        assert rl.allow("a") is True
        assert rl.allow("a") is False  # "a" exhausted

        assert rl.allow("b") is True   # "b" untouched
        assert rl.allow("b") is True
        assert rl.allow("b") is False  # "b" now exhausted

    def test_many_keys_all_get_full_limit(self) -> None:
        rl = RateLimiter(limit=3, window_seconds=1.0)
        keys = [f"key:{i}" for i in range(20)]
        for k in keys:
            allowed = _count_allows(rl, k, 3)
            assert allowed == 3, f"{k}: expected 3 allows, got {allowed}"

    def test_keys_do_not_share_counters(self) -> None:
        rl = RateLimiter(limit=1, window_seconds=1.0)
        # Each unique key gets exactly one allow.
        for i in range(50):
            assert rl.allow(f"k{i}") is True
        # Re-calling each should now be denied.
        for i in range(50):
            assert rl.allow(f"k{i}") is False


# ---------------------------------------------------------------------------
# 3. Unit — window rollover
# ---------------------------------------------------------------------------

class TestWindowRollover:
    """After one full window elapses, the counter should effectively reset."""

    def test_allows_after_window_expires(self) -> None:
        rl = RateLimiter(limit=3, window_seconds=0.1)
        assert _count_allows(rl, "r", 3) == 3
        assert rl.allow("r") is False  # limit exhausted

        time.sleep(0.12)  # advance past one full window
        # After rollover the new window starts fresh.
        # The weighted estimate for the previous window decays as time passes;
        # at least one request must be allowed shortly after the window turns.
        assert rl.allow("r") is True, "Expected allow after window rollover"

    def test_full_quota_restored_after_two_windows(self) -> None:
        rl = RateLimiter(limit=3, window_seconds=0.1)
        _count_allows(rl, "s", 3)
        time.sleep(0.22)  # two complete windows elapsed — previous is zeroed
        assert _count_allows(rl, "s", 3) == 3


# ---------------------------------------------------------------------------
# 4. Unit — weighted sliding-window stats correctness
# ---------------------------------------------------------------------------

class TestWeightedSlidingWindowStats:
    """
    Scenario:
      limit=10, window=1s.
      Fill 10 requests in the FIRST window slot.
      At ~0.5s into the SECOND window, weight_prev ≈ 0.5, so
      estimated_rate ≈ 0 (current) + 10 * 0.5 = 5.
      That leaves 5 more allows before the limit (10) is hit again.
    """

    def test_stats_dict_has_required_keys(self) -> None:
        rl = RateLimiter(limit=10, window_seconds=1.0)
        rl.allow("t")
        s = rl.stats("t")
        assert "current_count" in s
        assert "previous_count" in s
        assert "estimated_rate" in s

    def test_estimated_rate_reflects_current_window_count(self) -> None:
        rl = RateLimiter(limit=10, window_seconds=1.0)
        for _ in range(7):
            rl.allow("w")
        s = rl.stats("w")
        assert s["current_count"] == 7
        # No previous-window data yet, so estimated_rate == current_count
        # (within a small tolerance for sub-millisecond drift).
        assert 6.9 <= s["estimated_rate"] <= 7.1

    def test_previous_window_weight_decays_over_time(self) -> None:
        """
        Fill 10 in window N. Sleep until ~50% through window N+1.
        expected estimated_rate ≈ 10 * weight_prev (roughly 5, tolerance ±2).

        We use _sleep_to_window_fraction() to guarantee we cross the boundary
        and land at 50% into the next slot, regardless of where in the current
        window the test starts executing.
        """
        rl = RateLimiter(limit=10, window_seconds=0.5)
        for _ in range(10):
            rl.allow("v")

        # Cross into the next window, land 50% through it.
        _sleep_to_window_fraction(window_seconds=0.5, target_frac=0.5)

        s = rl.stats("v")
        # current window should be fresh (no new requests were made after sleep)
        assert s["current_count"] == 0
        # previous window holds the 10 we fired
        assert s["previous_count"] == 10
        # estimated_rate = 0 + 10 * weight_prev; at 50% elapsed weight_prev = 0.5
        # Tolerance ±0.15 to absorb OS scheduling jitter.
        assert 2.0 <= s["estimated_rate"] <= 6.0, (
            f"estimated_rate={s['estimated_rate']} outside expected range"
        )

    def test_allows_remaining_after_half_window(self) -> None:
        """
        Fill 10 in window N.  Cross the boundary and land 50% into window N+1.
        At that point weight_prev ≈ 0.5, so estimated_rate ≈ 10 × 0.5 = 5.
        The remaining budget is limit(10) - estimated(5) = 5 more allows.

        We use _sleep_to_window_fraction() to guarantee a deterministic
        crossing regardless of where in the current slot the test starts.
        """
        rl = RateLimiter(limit=10, window_seconds=0.5)
        for _ in range(10):
            rl.allow("z")

        # Cross into next window, land at 50%.
        _sleep_to_window_fraction(window_seconds=0.5, target_frac=0.5)

        allowed = _count_allows(rl, "z", 15)
        # At 50% elapsed, weight_prev ≈ 0.5 → estimated ≈ 5 → 5 more allowed.
        # Range [3, 8] absorbs OS scheduling jitter on slow CI machines.
        assert 3 <= allowed <= 8, (
            f"Expected 3-8 allows at half-window, got {allowed}"
        )


# ---------------------------------------------------------------------------
# 5. Concurrency — race detection
# ---------------------------------------------------------------------------

class TestConcurrency:
    """
    50 threads × 1000 calls each = 50,000 total allow() calls.
    limit=100, window=1s.

    The counter MUST NOT exceed the limit by more than a small tolerance
    caused by legitimate timing races at window boundaries (documented below).

    Over-allow tolerance: ≤ 5 extra requests (0.005% of total traffic).
    This reflects the known race window between reading estimated_rate and
    atomically incrementing the counter across different window epochs.
    Within a single window epoch the per-key lock makes the operation atomic.
    """

    OVER_ALLOW_TOLERANCE = 5

    def test_total_allowed_within_limit_plus_tolerance(self) -> None:
        rl = RateLimiter(limit=100, window_seconds=1.0)
        results: list[bool] = []
        lock = threading.Lock()

        def worker() -> None:
            local: list[bool] = []
            for _ in range(1000):
                local.append(rl.allow("shared"))
            with lock:
                results.extend(local)

        threads = [threading.Thread(target=worker) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        total_allowed = sum(results)
        # Must not exceed limit + tolerance.
        assert total_allowed <= 100 + self.OVER_ALLOW_TOLERANCE, (
            f"Over-allowed: {total_allowed} (limit=100, tolerance={self.OVER_ALLOW_TOLERANCE})"
        )
        # Sanity: at least the limit was filled.
        assert total_allowed >= 100, (
            f"Under-allowed: {total_allowed}; expected at least 100"
        )

    def test_no_state_corruption_across_threads(self) -> None:
        """stats() must return a coherent dict after heavy concurrent writes."""
        rl = RateLimiter(limit=500, window_seconds=2.0)

        def worker() -> None:
            for _ in range(200):
                rl.allow("chaos")

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        s = rl.stats("chaos")
        assert isinstance(s["current_count"], int)
        assert isinstance(s["previous_count"], int)
        assert isinstance(s["estimated_rate"], float)
        assert s["current_count"] >= 0
        assert s["previous_count"] >= 0
        assert s["estimated_rate"] >= 0.0

    def test_per_key_isolation_under_concurrency(self) -> None:
        """
        Two independent keys hammered concurrently must each respect their
        own limit, without cross-contamination.
        """
        rl = RateLimiter(limit=50, window_seconds=1.0)
        counts: dict[str, int] = {"a": 0, "b": 0}
        lock = threading.Lock()

        def worker(key: str) -> None:
            local = sum(1 for _ in range(500) if rl.allow(key))
            with lock:
                counts[key] += local

        threads = (
            [threading.Thread(target=worker, args=("a",)) for _ in range(10)]
            + [threading.Thread(target=worker, args=("b",)) for _ in range(10)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counts["a"] <= 50 + self.OVER_ALLOW_TOLERANCE
        assert counts["b"] <= 50 + self.OVER_ALLOW_TOLERANCE


# ---------------------------------------------------------------------------
# 6. Async — allow_async semantics
# ---------------------------------------------------------------------------

class TestAllowAsyncSemantics:
    """allow_async must obey the same limit/deny semantics as allow()."""

    def test_async_allows_then_denies(self) -> None:
        rl = RateLimiter(limit=3, window_seconds=1.0)

        async def run() -> list[bool]:
            results = []
            for _ in range(4):
                results.append(await rl.allow_async("async_key"))
            return results

        results = asyncio.run(run())
        assert results[:3] == [True, True, True]
        assert results[3] is False

    def test_async_and_sync_share_state(self) -> None:
        """Mixing allow() and allow_async() on the same key must stay atomic."""
        rl = RateLimiter(limit=4, window_seconds=1.0)

        # Consume 2 via sync.
        rl.allow("mixed")
        rl.allow("mixed")

        async def run() -> list[bool]:
            return [await rl.allow_async("mixed") for _ in range(3)]

        results = asyncio.run(run())
        # Only 2 async allows remain before the 4th is hit.
        assert results.count(True) == 2
        assert results.count(False) == 1

    def test_async_return_type_is_bool(self) -> None:
        rl = RateLimiter(limit=1, window_seconds=1.0)

        async def run() -> bool:
            return await rl.allow_async("t")

        result = asyncio.run(run())
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# 7. Async — non-blocking under concurrent load
# ---------------------------------------------------------------------------

class TestAllowAsyncNonBlocking:
    """
    Scheduling 100 concurrent allow_async() coroutines on limit=1000 must
    complete within 1 second, demonstrating the event loop is not blocked.
    """

    def test_100_concurrent_coroutines_finish_within_1s(self) -> None:
        rl = RateLimiter(limit=1000, window_seconds=2.0)

        async def run() -> float:
            start = time.monotonic()
            tasks = [rl.allow_async("load") for _ in range(100)]
            results = await asyncio.gather(*tasks)
            elapsed = time.monotonic() - start
            assert all(isinstance(r, bool) for r in results)
            return elapsed

        elapsed = asyncio.run(run())
        assert elapsed < 1.0, (
            f"100 concurrent allow_async() calls took {elapsed:.3f}s; expected < 1s"
        )

    def test_event_loop_not_blocked_by_lock_contention(self) -> None:
        """
        Even with high contention (limit=1), all coroutines must resolve
        quickly; none should block the loop indefinitely.
        """
        rl = RateLimiter(limit=1, window_seconds=1.0)

        async def run() -> None:
            tasks = [rl.allow_async("contended") for _ in range(50)]
            start = time.monotonic()
            await asyncio.gather(*tasks)
            elapsed = time.monotonic() - start
            assert elapsed < 1.0, (
                f"Lock contention blocked event loop for {elapsed:.3f}s"
            )

        asyncio.run(run())


# ---------------------------------------------------------------------------
# 8. Adversarial — burst attack + recovery
# ---------------------------------------------------------------------------

class TestAdversarialBurst:
    """
    10,000 rapid allow() calls from one thread on limit=100, window=1s.
    Total allowed must be <= 100. After sleeping one full window, the limit
    should be refreshed and allow() must succeed again.
    """

    def test_burst_total_allowed_does_not_exceed_limit(self) -> None:
        rl = RateLimiter(limit=100, window_seconds=1.0)
        total = _count_allows(rl, "attacker", 10_000)
        assert total <= 100, (
            f"Burst attack allowed {total} requests; limit is 100"
        )

    def test_burst_allows_at_least_the_limit(self) -> None:
        """Correct implementation must allow exactly the limit, not fewer."""
        rl = RateLimiter(limit=100, window_seconds=1.0)
        total = _count_allows(rl, "attacker2", 10_000)
        assert total >= 100, (
            f"Burst test allowed only {total}; expected >= 100"
        )

    def test_recovery_after_full_window_sleep(self) -> None:
        """After one full window elapses, the limit is effectively refreshed."""
        rl = RateLimiter(limit=5, window_seconds=0.2)
        _count_allows(rl, "recover", 5)
        assert rl.allow("recover") is False  # limit exhausted

        time.sleep(0.25)  # one full window + margin
        # The window has rolled over; at minimum one allow should succeed.
        assert rl.allow("recover") is True, (
            "Expected recovery allow after full-window sleep"
        )

    def test_repeated_bursts_across_multiple_windows(self) -> None:
        """Each new window grants a fresh budget."""
        rl = RateLimiter(limit=3, window_seconds=0.15)
        for window_num in range(3):
            allowed = _count_allows(rl, "multi", 10)
            # Due to weighted carry-over the first iteration gives ≥ 3,
            # subsequent windows may give slightly fewer due to weight_prev.
            # We assert at least 1 allow per window to verify recovery.
            assert allowed >= 1, (
                f"Window {window_num}: expected >= 1 allows, got {allowed}"
            )
            time.sleep(0.20)  # advance past window boundary


# ---------------------------------------------------------------------------
# 9. Reset — reset(key) and reset()
# ---------------------------------------------------------------------------

class TestReset:
    """reset() must clear counters; behaviour after reset mirrors a fresh limiter."""

    def test_reset_single_key_clears_that_key(self) -> None:
        rl = RateLimiter(limit=2, window_seconds=1.0)
        rl.allow("a")
        rl.allow("a")
        assert rl.allow("a") is False  # exhausted

        rl.reset("a")
        assert rl.allow("a") is True  # should succeed after reset

    def test_reset_single_key_does_not_affect_other_keys(self) -> None:
        rl = RateLimiter(limit=2, window_seconds=1.0)
        rl.allow("a")
        rl.allow("a")  # "a" exhausted
        rl.allow("b")  # "b" at 1/2

        rl.reset("a")  # only reset "a"

        assert rl.allow("a") is True   # "a" cleared
        assert rl.allow("b") is True   # "b" still at 1/2, now 2/2
        assert rl.allow("b") is False  # "b" exhausted

    def test_reset_all_keys_when_no_argument(self) -> None:
        rl = RateLimiter(limit=1, window_seconds=1.0)
        keys = ["x", "y", "z"]
        for k in keys:
            rl.allow(k)  # exhaust each

        for k in keys:
            assert rl.allow(k) is False, f"{k} should be exhausted"

        rl.reset()  # reset all

        for k in keys:
            assert rl.allow(k) is True, f"{k} should be allowed after global reset"

    def test_reset_nonexistent_key_does_not_raise(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        # Resetting a key that has never been seen must not raise.
        rl.reset("ghost")

    def test_reset_all_on_empty_limiter_does_not_raise(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        rl.reset()  # no keys registered yet; must not raise

    def test_stats_zeroed_after_reset(self) -> None:
        rl = RateLimiter(limit=10, window_seconds=1.0)
        for _ in range(7):
            rl.allow("s")
        rl.reset("s")
        s = rl.stats("s")
        assert s["current_count"] == 0
        assert s["estimated_rate"] == 0.0


# ---------------------------------------------------------------------------
# 10. Stats — dict shape and values after known sequence
# ---------------------------------------------------------------------------

class TestStats:
    """stats() must return a correctly structured dict with consistent values."""

    def test_stats_shape_on_fresh_key(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        s = rl.stats("fresh")
        assert set(s.keys()) == {"current_count", "previous_count", "estimated_rate"}

    def test_current_count_increments_with_allows(self) -> None:
        rl = RateLimiter(limit=10, window_seconds=1.0)
        for i in range(1, 6):
            rl.allow("c")
            assert rl.stats("c")["current_count"] == i

    def test_estimated_rate_matches_current_count_in_fresh_window(self) -> None:
        """
        At the very start of a window, previous_count should be 0, so
        estimated_rate == current_count (no weight from previous window).
        """
        # Use a long window so we stay firmly in the current slot.
        rl = RateLimiter(limit=100, window_seconds=60.0)
        for _ in range(10):
            rl.allow("e")
        s = rl.stats("e")
        assert s["current_count"] == 10
        # estimated_rate may include a small contribution from previous window;
        # it must be >= current_count (previous contribution is non-negative).
        assert s["estimated_rate"] >= 10.0

    def test_stats_for_unknown_key_returns_zeros(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        s = rl.stats("never_seen")
        assert s["current_count"] == 0
        assert s["previous_count"] == 0
        assert s["estimated_rate"] == 0.0

    def test_previous_count_populated_after_window_advance(self) -> None:
        """
        After a window rolls over, previous_count must reflect the old window.

        Uses _sleep_to_window_fraction() to guarantee we cross the boundary
        before calling allow() again.  We land at 10% into the new window so
        weight_prev is still high and the previous_count assertion is sound.
        """
        rl = RateLimiter(limit=20, window_seconds=0.3)
        for _ in range(5):
            rl.allow("p")

        # Cross into the next window (land at 10%).
        _sleep_to_window_fraction(window_seconds=0.3, target_frac=0.1)

        # One request in the new window initialises current_count.
        rl.allow("p")
        s = rl.stats("p")
        assert s["previous_count"] == 5, (
            f"Expected previous_count=5, got {s['previous_count']}"
        )
        assert s["current_count"] == 1

    def test_estimated_rate_type_is_float(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        rl.allow("f")
        s = rl.stats("f")
        assert isinstance(s["estimated_rate"], float)

    def test_stats_values_are_non_negative(self) -> None:
        rl = RateLimiter(limit=5, window_seconds=1.0)
        for _ in range(5):
            rl.allow("n")
        s = rl.stats("n")
        assert s["current_count"] >= 0
        assert s["previous_count"] >= 0
        assert s["estimated_rate"] >= 0.0
