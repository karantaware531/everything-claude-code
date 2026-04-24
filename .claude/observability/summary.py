#!/usr/bin/env python3
"""
summary.py — human-readable summary of observability traces.

Reads .claude/observability/traces.json and prints:
    - per-agent: invocations, pass rate, median duration
    - recent failures (last 5)
    - trust-matrix highlights
    - a one-line overall health indicator

Usage:
    python summary.py                 # prints last 20 traces' aggregates
    python summary.py --limit 100     # wider window
    python summary.py --agent code_agent  # filter to one agent

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
TRACES = ROOT / "observability" / "traces.json"
TRUST = ROOT / "memory" / "trust_matrix.json"


def _load_json(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def summarize(traces: list[dict], agent_filter: str | None = None) -> None:
    if not traces:
        print("No traces yet. (execution_engine will populate observability/traces.json on first task.)")
        return

    per_agent_durations: dict[str, list[int]] = defaultdict(list)
    per_agent_invocations: Counter[str] = Counter()
    per_agent_failures: Counter[str] = Counter()
    recent_failures: list[dict] = []

    for tr in traces:
        durations = tr.get("durations_ms", {}) or {}
        failures = tr.get("failures", []) or []
        agents = tr.get("agents_used", []) or []

        for a in agents:
            if agent_filter and a != agent_filter:
                continue
            per_agent_invocations[a] += 1
            d = durations.get(a)
            if isinstance(d, (int, float)):
                per_agent_durations[a].append(int(d))

        for f in failures:
            a = f.get("agent", "?")
            if agent_filter and a != agent_filter:
                continue
            per_agent_failures[a] += 1
            recent_failures.append({
                "task_id": tr.get("task_id"),
                "agent": a,
                "reason": f.get("reason"),
                "started_at": tr.get("started_at"),
            })

    # ── Per-agent table ──────────────────────────────────────────────────────
    print("PER-AGENT STATS")
    print("-" * 72)
    header = f"{'agent':<28}{'calls':>8}{'fails':>8}{'pass%':>8}{'p50_ms':>10}"
    print(header)
    print("-" * 72)
    for agent in sorted(per_agent_invocations.keys()):
        calls = per_agent_invocations[agent]
        fails = per_agent_failures[agent]
        pct = 100.0 * (calls - fails) / calls if calls else 0.0
        durs = per_agent_durations.get(agent, [])
        p50 = int(statistics.median(durs)) if durs else 0
        print(f"{agent:<28}{calls:>8}{fails:>8}{pct:>7.1f}%{p50:>10}")
    print()

    # ── Recent failures ──────────────────────────────────────────────────────
    recent_failures = recent_failures[-5:]
    if recent_failures:
        print("RECENT FAILURES (last 5)")
        print("-" * 72)
        for f in recent_failures:
            print(f"  {f['started_at']}  [{f['agent']}]  task={f['task_id']}")
            if f.get("reason"):
                print(f"      reason: {f['reason']}")
        print()


def summarize_trust(trust: dict, agent_filter: str | None = None) -> None:
    pairs = trust.get("pairs", {}) or {}
    if not pairs:
        return

    print("TRUST MATRIX HIGHLIGHTS (top & bottom 3 by pass_rate, n ≥ 3)")
    print("-" * 72)
    eligible: list[tuple[str, dict]] = []
    for key, stats in pairs.items():
        if not isinstance(stats, dict):
            continue
        if stats.get("n", 0) < 3:
            continue
        if agent_filter and agent_filter not in key:
            continue
        eligible.append((key, stats))
    if not eligible:
        print("  (not enough history yet — trust requires n ≥ 3 per pair)")
        return

    eligible.sort(key=lambda kv: kv[1].get("pass_rate", 0.0), reverse=True)
    for key, stats in eligible[:3]:
        print(f"  + {key:<40} pass={stats.get('pass_rate', 0):.2f}  n={stats.get('n', 0)}")
    if len(eligible) > 3:
        for key, stats in eligible[-3:]:
            print(f"  - {key:<40} pass={stats.get('pass_rate', 0):.2f}  n={stats.get('n', 0)}")
    print()


def health_line(traces: list[dict]) -> str:
    total = len(traces)
    if total == 0:
        return "HEALTH: no traces yet"
    fails = sum(len(t.get("failures", []) or []) for t in traces)
    rate = 100.0 * (1 - fails / max(1, sum(len(t.get("agents_used", []) or []) for t in traces)))
    return f"HEALTH: {total} traces, pass rate ~{rate:.1f}%"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, default=20, help="how many most-recent traces to include")
    parser.add_argument("--agent", type=str, default=None, help="filter to a single agent name")
    args = parser.parse_args(argv)

    traces_data = _load_json(TRACES, {"traces": []})
    trust_data = _load_json(TRUST, {"pairs": {}})
    traces = traces_data.get("traces", [])[-max(1, args.limit):]

    print(health_line(traces))
    print()
    summarize(traces, args.agent)
    summarize_trust(trust_data, args.agent)
    return 0


if __name__ == "__main__":
    sys.exit(main())
