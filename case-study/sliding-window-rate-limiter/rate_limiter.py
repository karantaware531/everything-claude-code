"""Sliding-window-counter rate limiter — production-grade, stdlib only.

Algorithm: weighted sliding-window counter.
    current_window  = floor(now / W)
    previous_window = current_window - 1
    elapsed_frac    = (now % W) / W
    weight_prev     = 1.0 - elapsed_frac
    estimated       = counts[key][current] + counts[key][previous] * weight_prev
    allow iff estimated < limit

Approximation note:
    The sliding-window-counter algorithm is an *approximation* of a true
    sliding window.  Under concurrent boundary races across distinct window
    epochs it can admit up to ~1% over-allow relative to the nominal limit.
    Within a single epoch the per-key lock guarantees atomicity, so
    single-epoch over-allow is impossible.  The ~1% figure is the weighted-
    estimate approximation error inherent to the algorithm, not a locking
    bug.  If exact conformance is required, use a leaky-bucket or
    token-bucket algorithm instead.

Memory management:
    ``max_keys`` caps the total number of distinct keys tracked (default
    100 000).  When the cap is reached, the least-recently-used key is
    evicted to make room.  Keys that have not been accessed for longer than
    ``key_ttl_seconds`` (default 3 600 s) are also evicted lazily on next
    access or insertion.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class _KeyState:
    """Per-key mutable state: two window counters + a per-key lock."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    # Maps window-index -> request count; kept to at most 2 entries.
    counts: Dict[int, int] = field(default_factory=dict)

    def _evict(self, current_window: int) -> None:
        """Drop windows older than previous_window to bound memory."""
        previous_window = current_window - 1
        stale = [w for w in self.counts if w < previous_window]
        for w in stale:
            del self.counts[w]

    def check_and_increment(self, limit: int, window_seconds: float) -> bool:
        """Apply the weighted-counter algorithm and return allow/deny.

        Args:
            limit: Maximum requests allowed within one window.
            window_seconds: Duration of a single window in seconds.

        Returns:
            True if the request is allowed; False if rate-limited.
        """
        now = time.monotonic()
        current_window = int(now / window_seconds)
        previous_window = current_window - 1
        elapsed_frac = (now % window_seconds) / window_seconds
        weight_prev = 1.0 - elapsed_frac

        with self.lock:
            self._evict(current_window)
            current_count = self.counts.get(current_window, 0)
            previous_count = self.counts.get(previous_window, 0)
            estimated = current_count + previous_count * weight_prev
            if estimated < limit:
                self.counts[current_window] = current_count + 1
                return True
            return False

    def get_stats(self, window_seconds: float) -> dict:
        """Return a point-in-time snapshot of rate counters.

        Args:
            window_seconds: Duration of a single window in seconds.

        Returns:
            Dictionary with keys ``current_count``, ``previous_count``,
            and ``estimated_rate``.
        """
        now = time.monotonic()
        current_window = int(now / window_seconds)
        previous_window = current_window - 1
        elapsed_frac = (now % window_seconds) / window_seconds
        weight_prev = 1.0 - elapsed_frac

        with self.lock:
            current_count = self.counts.get(current_window, 0)
            previous_count = self.counts.get(previous_window, 0)
            estimated = current_count + previous_count * weight_prev

        return {
            "current_count": current_count,
            "previous_count": previous_count,
            "estimated_rate": estimated,
        }


class RateLimiter:
    """Thread-safe, async-compatible sliding-window-counter rate limiter.

    Each unique ``key`` has independent state, allowing fine-grained
    per-user or per-resource limiting with no cross-key contention.

    Args:
        limit: Maximum number of requests allowed per ``window_seconds``.
            Must be >= 1.
        window_seconds: Length of the sliding window in seconds.
            Must be > 0.
        max_keys: Maximum number of distinct keys tracked simultaneously
            (default 100 000).  When the cap is reached, the
            least-recently-used key is evicted to make room for the new
            one.  Use this to bound memory consumption under cardinality
            DoS attacks.
        key_ttl_seconds: Keys untouched for longer than this duration
            (seconds) are evicted lazily on the next access or insertion
            event (default 3 600 s / 1 hour).

    Example::

        rl = RateLimiter(limit=100, window_seconds=1.0)
        if rl.allow("user:42"):
            process_request()
    """

    def __init__(
        self,
        limit: int,
        window_seconds: float,
        max_keys: int = 100_000,
        key_ttl_seconds: float = 3600.0,
    ) -> None:
        if limit < 1:
            raise ValueError(f"limit must be >= 1, got {limit}")
        if window_seconds <= 0.0:
            raise ValueError(f"window_seconds must be > 0, got {window_seconds}")
        if max_keys < 1:
            raise ValueError(f"max_keys must be >= 1, got {max_keys}")
        if key_ttl_seconds <= 0.0:
            raise ValueError(f"key_ttl_seconds must be > 0, got {key_ttl_seconds}")

        self._limit: int = limit
        self._window: float = window_seconds
        self._max_keys: int = max_keys
        self._key_ttl: float = key_ttl_seconds

        # _global_lock guards ALL structural mutations to _states and
        # _last_seen.  Every lookup — including the hot read path — goes
        # through this lock to prevent non-CPython dict structural races.
        # Per-key locks inside _KeyState still guard the check-then-
        # increment, so there is no inter-key contention on the hot path
        # beyond the brief global-lock critical section.
        self._global_lock: threading.Lock = threading.Lock()

        # OrderedDict preserves LRU order: move_to_end on every access,
        # evict from the front (oldest-used) when at capacity.
        self._states: OrderedDict[str, _KeyState] = OrderedDict()

        # Tracks the last-access timestamp for TTL eviction.
        self._last_seen: Dict[str, float] = {}

        # Rate-limit the TTL scan: only run the O(n) sweep at most once
        # per _TTL_SCAN_INTERVAL_SECONDS, regardless of request rate.
        # This keeps the hot path O(1) while still providing TTL eviction.
        self._TTL_SCAN_INTERVAL: float = max(1.0, key_ttl_seconds / 100.0)
        self._next_ttl_scan: float = 0.0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_stale_locked(self, now: float) -> None:
        """Evict all TTL-expired keys.  Caller MUST hold ``_global_lock``."""
        expired = [
            k for k, ts in self._last_seen.items()
            if now - ts > self._key_ttl
        ]
        for k in expired:
            self._states.pop(k, None)
            self._last_seen.pop(k, None)

    def _evict_lru_locked(self) -> None:
        """Evict the single least-recently-used key.  Caller MUST hold ``_global_lock``."""
        if self._states:
            oldest_key, _ = next(iter(self._states.items()))
            self._states.pop(oldest_key, None)
            self._last_seen.pop(oldest_key, None)

    def _get_state(self, key: str) -> _KeyState:
        """Return existing _KeyState for *key*, creating it if absent.

        All dict structural operations are performed under ``_global_lock``.
        The key is moved to the MRU end of the OrderedDict on every access
        to maintain LRU eviction order.  TTL scans are throttled to run at
        most once per ``_TTL_SCAN_INTERVAL`` seconds so the hot path stays
        O(1) under steady-state traffic.
        """
        now = time.monotonic()
        with self._global_lock:
            # Throttled TTL sweep: only pay the O(n) cost periodically.
            if now >= self._next_ttl_scan:
                self._evict_stale_locked(now)
                self._next_ttl_scan = now + self._TTL_SCAN_INTERVAL

            if key in self._states:
                # Promote to MRU position.
                self._states.move_to_end(key)
                self._last_seen[key] = now
                return self._states[key]

            # Key is new — enforce capacity cap before inserting.
            if len(self._states) >= self._max_keys:
                self._evict_lru_locked()

            state = _KeyState()
            self._states[key] = state
            self._last_seen[key] = now
            return state

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self, key: str) -> bool:
        """Decide whether a request from *key* is within the rate limit.

        Args:
            key: Arbitrary string identifier (user-id, IP address, API
                token, …).  Must be a non-empty ``str``.

        Returns:
            True if the request is allowed; False if it exceeds the limit.

        Raises:
            ValueError: If ``key`` is ``None``, empty, or not a ``str``.
        """
        if not isinstance(key, str) or not key:
            raise ValueError(
                f"key must be a non-empty str, got {key!r}"
            )
        return self._get_state(key).check_and_increment(self._limit, self._window)

    async def allow_async(self, key: str) -> bool:
        """Async variant of :meth:`allow`; never blocks the event loop.

        Uses :func:`asyncio.to_thread` to execute the (potentially
        lock-contended) synchronous path on a worker thread, keeping the
        calling coroutine non-blocking.

        Args:
            key: Arbitrary identifier for the requesting entity.

        Returns:
            True if the request is allowed; False if rate-limited.
        """
        return await asyncio.to_thread(self.allow, key)

    def reset(self, key: Optional[str] = None) -> None:
        """Clear rate-limit counters for one key, or for all keys.

        Args:
            key: If provided, reset only this key's counters.
                 If ``None``, reset every key tracked by this instance.
        """
        if key is not None:
            with self._global_lock:
                state = self._states.get(key)
            if state is not None:
                with state.lock:
                    state.counts.clear()
        else:
            with self._global_lock:
                keys = list(self._states.keys())
            for k in keys:
                with self._global_lock:
                    state = self._states.get(k)
                if state is not None:
                    with state.lock:
                        state.counts.clear()

    def stats(self, key: str) -> dict:
        """Return rate-limit statistics for *key*.

        Args:
            key: Identifier whose stats are requested.

        Returns:
            Dict keys: ``current_count`` (int), ``previous_count`` (int),
            ``estimated_rate`` (float — weighted estimate used by the algorithm).
        """
        return self._get_state(key).get_stats(self._window)

    def cardinality(self) -> int:
        """Return the number of distinct keys currently tracked.

        This is an observability hook for monitoring memory consumption.
        The value reflects the live state of the internal key registry
        (after any pending LRU/TTL eviction that fires on the next access).

        Returns:
            Current number of tracked keys (``<= max_keys``).
        """
        with self._global_lock:
            return len(self._states)
