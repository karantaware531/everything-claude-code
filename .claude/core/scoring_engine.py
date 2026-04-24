#!/usr/bin/env python3
"""
scoring_engine.py — agent performance + trust bookkeeping.

Persists to:
    .claude/memory/agent_history.json       (per-invocation records)
    .claude/memory/trust_matrix.json        (producer→consumer pair stats)

Additive to the v1 schema: old entries remain valid; new entries carry
`metrics` (duration_ms, tokens) and optional `caller` (for trust).

Usage (CLI):
    python scoring_engine.py --record --agent code_agent --task t-123 \\
        --duration 420 --tokens 800 --accuracy 0.9 --success true --caller planner
    python scoring_engine.py --stats code_agent
    python scoring_engine.py --trust planner code_agent

Usage (library):
    from scoring_engine import record, stats, trust_stats, update_trust

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
MEMORY = ROOT / "memory"
HISTORY = MEMORY / "agent_history.json"
TRUST = MEMORY / "trust_matrix.json"

LAPLACE_ALPHA = 1.0  # cold-start smoothing for pass_rate

DEFAULT_STATS = {
    "n": 0,
    "success_rate": 0.7,   # optimistic default until we have data
    "accuracy": 0.7,
    "duration_p50_ms": 1000,
    "tokens_p50": 500,
    "cost_efficiency": 1.0,
}


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(path)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record(agent: str, task_id: str, duration_ms: int, tokens: int,
           accuracy: float, success: bool, caller: str | None = None,
           extra: dict | None = None) -> dict:
    """Append a per-invocation record and update trust (if caller given)."""
    data = _load(HISTORY, {"entries": [], "version": 1})
    entry = {
        "agent":       agent,
        "task_id":     task_id,
        "timestamp":   _now(),
        "metrics":     {"duration_ms": int(duration_ms), "tokens": int(tokens)},
        "accuracy":    float(accuracy),
        "success":     bool(success),
        "caller":      caller,
    }
    if extra:
        entry.update(extra)
    data.setdefault("entries", []).append(entry)
    _atomic_write(HISTORY, data)

    if caller:
        update_trust(caller, agent, success)

    return entry


def stats(agent: str) -> dict:
    """Aggregate stats for one agent. Defaults returned when no history."""
    data = _load(HISTORY, {"entries": []})
    entries = [e for e in data.get("entries", []) if e.get("agent") == agent]
    if not entries:
        return {"agent": agent, **DEFAULT_STATS}

    n = len(entries)
    successes = sum(1 for e in entries if e.get("success"))
    # Laplace smoothing: (successes + α) / (n + 2α) with α=1 → ≈ (s+1)/(n+2)
    pass_rate = (successes + LAPLACE_ALPHA) / (n + 2 * LAPLACE_ALPHA)

    accuracies = [float(e.get("accuracy", 0.0)) for e in entries]
    accuracy = sum(accuracies) / len(accuracies) if accuracies else 0.0

    durs = [int(e.get("metrics", {}).get("duration_ms", 0)) for e in entries if e.get("metrics")]
    tokens = [int(e.get("metrics", {}).get("tokens", 0)) for e in entries if e.get("metrics")]
    dur_p50 = int(statistics.median(durs)) if durs else 0
    tok_p50 = int(statistics.median(tokens)) if tokens else 0

    # cost_efficiency = 1 / (1 + duration_sec + 0.001 * tokens)
    ce = 1.0 / (1.0 + dur_p50 / 1000.0 + 0.001 * tok_p50) if (dur_p50 or tok_p50) else 1.0

    return {
        "agent":            agent,
        "n":                n,
        "success_rate":     round(pass_rate, 3),
        "accuracy":         round(accuracy, 3),
        "duration_p50_ms":  dur_p50,
        "tokens_p50":       tok_p50,
        "cost_efficiency":  round(ce, 3),
    }


# ─── Trust matrix ────────────────────────────────────────────────────────────

def _trust_key(caller: str, callee: str) -> str:
    return f"{caller}->{callee}"


def update_trust(caller: str, callee: str, success: bool) -> dict:
    """Update pair stats after an evaluator-pass or fail downstream."""
    data = _load(TRUST, {"version": 1, "pairs": {}})
    pairs = data.setdefault("pairs", {})
    key = _trust_key(caller, callee)
    pair = pairs.get(key) or {"n": 0, "passes": 0, "pass_rate": 0.0, "updated": None}
    pair["n"] = int(pair.get("n", 0)) + 1
    pair["passes"] = int(pair.get("passes", 0)) + (1 if success else 0)
    n, p = pair["n"], pair["passes"]
    # Laplace smoothing too
    pair["pass_rate"] = round((p + LAPLACE_ALPHA) / (n + 2 * LAPLACE_ALPHA), 3)
    pair["updated"] = _now()
    pairs[key] = pair
    data["updated_at"] = _now()
    _atomic_write(TRUST, data)
    return pair


def trust_stats(caller: str, callee: str) -> dict:
    data = _load(TRUST, {"pairs": {}})
    pair = data.get("pairs", {}).get(_trust_key(caller, callee))
    if not pair:
        return {"pair": _trust_key(caller, callee), "n": 0, "pass_rate": 0.7, "default": True}
    return {"pair": _trust_key(caller, callee), **pair, "default": False}


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_mutually_exclusive_group()
    sub.add_argument("--record", action="store_true", help="record an invocation")
    sub.add_argument("--stats", metavar="AGENT", help="print aggregate stats for an agent")
    sub.add_argument("--trust", metavar=("CALLER", "CALLEE"), nargs=2, help="print trust stats for a pair")

    parser.add_argument("--agent", type=str)
    parser.add_argument("--task", type=str)
    parser.add_argument("--duration", type=int, default=0)
    parser.add_argument("--tokens", type=int, default=0)
    parser.add_argument("--accuracy", type=float, default=0.0)
    parser.add_argument("--success", type=str, default="false",
                        help="'true' or 'false'")
    parser.add_argument("--caller", type=str, default=None)

    args = parser.parse_args(argv)

    if args.record:
        if not (args.agent and args.task):
            print("ERROR: --record requires --agent and --task", file=sys.stderr)
            return 2
        success = str(args.success).lower() in ("true", "1", "yes", "y")
        entry = record(args.agent, args.task, args.duration, args.tokens,
                       args.accuracy, success, args.caller)
        print(json.dumps(entry, indent=2))
        return 0

    if args.stats:
        print(json.dumps(stats(args.stats), indent=2))
        return 0

    if args.trust:
        caller, callee = args.trust
        print(json.dumps(trust_stats(caller, callee), indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
