#!/usr/bin/env python3
"""
session_health_probe.py \u2014 SessionStart hook.

On every new session, emit a compact health summary to stdout:
    * registry self-test status
    * agent count by layer
    * graph size
    * recent failure rate (if any)
    * suggested next action

Never blocks (exit 0 always). Informational only \u2014 the single source of truth
for system health remains `python .claude/tools/test_runner.py`.

Disable with AGENTIC_OS_HOOKS_DISABLED=1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REGISTRY = ROOT / "wiki" / "registry.json"
GRAPH = ROOT / "wiki" / "graph" / "graph.json"
AGENT_HISTORY = ROOT / "memory" / "agent_history.json"
VALIDATOR = ROOT / "tools" / "agent_validator.py"


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def main() -> int:
    if os.environ.get("AGENTIC_OS_HOOKS_DISABLED"):
        return 0
    try:
        _ = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        pass

    # Agent self-test \u2014 fast; degrades gracefully if validator is missing.
    registry_ok = None
    if VALIDATOR.exists():
        try:
            r = subprocess.run([sys.executable, str(VALIDATOR), "--self-test"],
                               capture_output=True, text=True, timeout=15)
            registry_ok = (r.returncode == 0)
        except (subprocess.TimeoutExpired, OSError):
            registry_ok = None

    # Agent count by layer.
    by_layer: dict[str, int] = {}
    agents = _load(REGISTRY, {"agents": []}).get("agents", []) or []
    for a in agents:
        layer = a.get("layer", "unknown")
        by_layer[layer] = by_layer.get(layer, 0) + 1

    # Graph size.
    graph = _load(GRAPH, {"nodes": []})
    node_count = len(graph.get("nodes", []) or [])
    edge_count = sum(len(n.get("relationships") or []) for n in graph.get("nodes", []) or [])

    # Recent failure rate over last 50 history entries.
    entries = _load(AGENT_HISTORY, {"entries": []}).get("entries", []) or []
    recent = entries[-50:]
    if recent:
        fails = sum(1 for e in recent if not e.get("success", True))
        fail_rate = round(fails / len(recent), 2)
    else:
        fail_rate = None

    # Emit the banner.
    print("[hook:session_health_probe] Agentic OS v5 session starting")
    print(f"  registry_ok:    {registry_ok if registry_ok is not None else 'unknown'}")
    print(f"  agents:         {len(agents)} ({', '.join(f'{k}={v}' for k, v in sorted(by_layer.items()))})")
    print(f"  graph:          {node_count} nodes, {edge_count} edges")
    if fail_rate is not None:
        print(f"  recent_failures: {fail_rate} over last {len(recent)} invocations")
    else:
        print("  recent_failures: (no history yet)")

    # Suggestions.
    if registry_ok is False:
        print("  -> run `python .claude/tools/test_runner.py` to diagnose.")
    if len(entries) >= 20:
        print("  -> epoch_learner is due: `python .claude/core/epoch_learner.py --window 20`")
    if fail_rate is not None and fail_rate >= 0.3:
        print("  -> failure rate is high; consider `performance_optimizer --mode global`.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
