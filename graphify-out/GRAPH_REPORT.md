# Graph Report - Agentic-AI  (2026-05-06)

## Corpus Check
- 3 files · ~13,866 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 114 nodes · 251 edges · 11 communities detected
- Extraction: 51% EXTRACTED · 49% INFERRED · 0% AMBIGUOUS · INFERRED: 123 edges (avg confidence: 0.71)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]

## God Nodes (most connected - your core abstractions)
1. `RateLimiter` - 87 edges
2. `_count_allows()` - 12 edges
3. `TestStats` - 10 edges
4. `TestBasicAllowDeny` - 9 edges
5. `TestReset` - 9 edges
6. `run()` - 8 edges
7. `TestWeightedSlidingWindowStats` - 7 edges
8. `TestAdversarialBurst` - 7 edges
9. `_KeyState` - 6 edges
10. `TestPerKeyIsolation` - 6 edges

## Surprising Connections (you probably didn't know these)
- `Benchmark: sliding-window-rate-limiter — single-threaded throughput.` --uses--> `RateLimiter`  [INFERRED]
  case-study\sliding-window-rate-limiter\bench.py → case-study\sliding-window-rate-limiter\rate_limiter.py
- `RateLimiter` --uses--> `pytest suite for rate_limiter.RateLimiter (sliding-window-counter algorithm).`  [INFERRED]
  case-study\sliding-window-rate-limiter\rate_limiter.py → case-study\sliding-window-rate-limiter\test_rate_limiter.py
- `RateLimiter` --uses--> `Sleep until the elapsed fraction within the NEXT window slot is approximately`  [INFERRED]
  case-study\sliding-window-rate-limiter\rate_limiter.py → case-study\sliding-window-rate-limiter\test_rate_limiter.py
- `RateLimiter` --uses--> `Call allow() n times and return the number of True results.`  [INFERRED]
  case-study\sliding-window-rate-limiter\rate_limiter.py → case-study\sliding-window-rate-limiter\test_rate_limiter.py
- `RateLimiter` --uses--> `limit=5, window=1s — burst of 5 must all pass; 6th must be denied.`  [INFERRED]
  case-study\sliding-window-rate-limiter\rate_limiter.py → case-study\sliding-window-rate-limiter\test_rate_limiter.py

## Communities

### Community 0 - "Community 0"
Cohesion: 0.16
Nodes (10): RateLimiter, Thread-safe, async-compatible sliding-window-counter rate limiter.      Each u, Async variant of :meth:`allow`; never blocks the event loop.          Uses :fu, Return the number of distinct keys currently tracked.          This is an obse, Different keys must have completely independent counters., 50 threads × 1000 calls each = 50,000 total allow() calls.     limit=100, windo, stats() must return a coherent dict after heavy concurrent writes., Two independent keys hammered concurrently must each respect their         own (+2 more)

### Community 1 - "Community 1"
Cohesion: 0.17
Nodes (8): Return rate-limit statistics for *key*.          Args:             key: Ident, Fill 10 in window N. Sleep until ~50% through window N+1.         expected esti, Sleep until the elapsed fraction within the NEXT window slot is approximately, stats() must return a correctly structured dict with consistent values., At the very start of a window, previous_count should be 0, so         estimated, After a window rolls over, previous_count must reflect the old window., _sleep_to_window_fraction(), TestStats

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (10): _count_allows(), pytest suite for rate_limiter.RateLimiter (sliding-window-counter algorithm)., After one full window elapses, the counter should effectively reset., 10,000 rapid allow() calls from one thread on limit=100, window=1s.     Total a, Correct implementation must allow exactly the limit, not fewer., After one full window elapses, the limit is effectively refreshed., Each new window grants a fresh budget., Call allow() n times and return the number of True results. (+2 more)

### Community 3 - "Community 3"
Cohesion: 0.13
Nodes (9): _KeyState, Sliding-window-counter rate limiter — production-grade, stdlib only.  Algorith, Evict all TTL-expired keys.  Caller MUST hold ``_global_lock``., Evict the single least-recently-used key.  Caller MUST hold ``_global_lock``., Return existing _KeyState for *key*, creating it if absent.          All dict, Per-key mutable state: two window counters + a per-key lock., Drop windows older than previous_window to bound memory., Apply the weighted-counter algorithm and return allow/deny.          Args: (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.17
Nodes (6): Decide whether a request from *key* is within the rate limit.          Args:, Scenario:       limit=10, window=1s.       Fill 10 requests in the FIRST windo, Fill 10 in window N.  Cross the boundary and land 50% into window N+1., limit=5, window=1s — burst of 5 must all pass; 6th must be denied., TestBasicAllowDeny, TestWeightedSlidingWindowStats

### Community 5 - "Community 5"
Cohesion: 0.17
Nodes (9): main(), Benchmark: sliding-window-rate-limiter — single-threaded throughput., run(), allow_async must obey the same limit/deny semantics as allow()., Mixing allow() and allow_async() on the same key must stay atomic., Scheduling 100 concurrent allow_async() coroutines on limit=1000 must     compl, Even with high contention (limit=1), all coroutines must resolve         quickl, TestAllowAsyncNonBlocking (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.31
Nodes (3): Clear rate-limit counters for one key, or for all keys.          Args:, reset() must clear counters; behaviour after reset mirrors a fresh limiter., TestReset

### Community 7 - "Community 7"
Cohesion: 1.0
Nodes (1): README

### Community 8 - "Community 8"
Cohesion: 1.0
Nodes (1): claude-code-best-practices-v5.4

### Community 9 - "Community 9"
Cohesion: 1.0
Nodes (1): v5.3-specialist-integration

### Community 10 - "Community 10"
Cohesion: 1.0
Nodes (1): v5.4-anthropic-best-practices

## Knowledge Gaps
- **18 isolated node(s):** `Sliding-window-counter rate limiter — production-grade, stdlib only.  Algorith`, `Per-key mutable state: two window counters + a per-key lock.`, `Drop windows older than previous_window to bound memory.`, `Apply the weighted-counter algorithm and return allow/deny.          Args:`, `Return a point-in-time snapshot of rate counters.          Args:` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 7`** (1 nodes): `README`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 8`** (1 nodes): `claude-code-best-practices-v5.4`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 9`** (1 nodes): `v5.3-specialist-integration`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 10`** (1 nodes): `v5.4-anthropic-best-practices`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RateLimiter` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`?**
  _High betweenness centrality (0.760) - this node is a cross-community bridge._
- **Why does `_count_allows()` connect `Community 2` to `Community 0`, `Community 4`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Are the 76 inferred relationships involving `RateLimiter` (e.g. with `Benchmark: sliding-window-rate-limiter — single-threaded throughput.` and `TestBasicAllowDeny`) actually correct?**
  _`RateLimiter` has 76 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Sliding-window-counter rate limiter — production-grade, stdlib only.  Algorith`, `Per-key mutable state: two window counters + a per-key lock.`, `Drop windows older than previous_window to bound memory.` to the rest of the system?**
  _18 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 3` be split into smaller, more focused modules?**
  _Cohesion score 0.13 - nodes in this community are weakly interconnected._