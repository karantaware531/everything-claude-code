#!/usr/bin/env python3
"""
execution_engine.py — DAG runner with retries, circuit breaker, cost sensor,
simulation mode, and HITL escalation.

Plan schema (produced by the `planner` agent, also accepted from workflows/*.json):

    {
      "task_id": "t-...",
      "goal":    "...",
      "nodes": [
        {
          "id":              "n1",
          "capability":      "<verb-phrase>",
          "input":           { ... },
          "expected_output": "...",
          "retries_allowed": 2,
          "assigned_agent":  "<name or null>"
        }
      ],
      "edges": [["n1","n2"]]
    }

Usage (CLI):
    python execution_engine.py --dry-run
    python execution_engine.py --simulate --plan '<json>'
    python execution_engine.py --simulate --plan-file workflows/debug_pipeline.json

Library mode (when Claude invokes this from within a subagent context):
    from execution_engine import simulate, run

NOTE: `run()` here is a *recorder*. It cannot synchronously invoke Claude Code
subagents from Python (that's the harness's job). Instead, it:
  - validates the DAG (simulate)
  - emits per-node protocol records + traces
  - tracks circuit-breaker state across recorded invocations
  - provides the scheduling hooks orchestrator uses

This keeps the engine deterministic and unit-testable while still giving the
orchestrator a single place to enforce the execution contract.

Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # .claude/
TRACES = ROOT / "observability" / "traces.json"
REGISTRY = ROOT / "registry.json"  # v5.2: moved from wiki/
SIM_HISTORY = ROOT / "memory" / "simulation_history.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from context_engine import build_context, context_hash, update_context  # noqa: E402
from scoring_engine import record as score_record  # noqa: E402
from agent_selector import select as select_agent  # noqa: E402
from uncertainty import aggregate as aggregate_uncertainty  # noqa: E402


# ─── DAG validation (simulation) ─────────────────────────────────────────────

def _topo_sort(nodes: list[dict], edges: list[list[str]]) -> list[str]:
    """Kahn's algorithm. Returns topological order or raises on cycle."""
    node_ids = [n["id"] for n in nodes]
    indeg: dict[str, int] = {nid: 0 for nid in node_ids}
    adj: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for src, dst in edges:
        if src not in adj or dst not in indeg:
            raise ValueError(f"edge references unknown node: {src} → {dst}")
        adj[src].append(dst)
        indeg[dst] += 1
    queue = [nid for nid, d in indeg.items() if d == 0]
    order: list[str] = []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        for nbr in adj[cur]:
            indeg[nbr] -= 1
            if indeg[nbr] == 0:
                queue.append(nbr)
    if len(order) != len(node_ids):
        raise ValueError("cycle detected in DAG")
    return order


def _capability_resolvable(capability: str, registry: dict) -> bool:
    """Any agent declaring this capability? Very loose token-overlap check."""
    target = set(capability.lower().split())
    for a in registry.get("agents", []):
        for cap in a.get("capabilities", []) or []:
            if target & set(cap.lower().split()):
                return True
    return False


def _dag_hash(plan: dict) -> str:
    """Stable hash of the DAG structure (node ids + capabilities + edges). v3."""
    skeleton = {
        "nodes": [(n.get("id"), n.get("capability")) for n in plan.get("nodes", []) or []],
        "edges": sorted(tuple(e) for e in (plan.get("edges") or [])),
    }
    blob = json.dumps(skeleton, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _append_simulation_history(entry: dict) -> None:
    """v3: record every simulation so planner can skip known-bad DAG shapes."""
    SIM_HISTORY.parent.mkdir(parents=True, exist_ok=True)
    if SIM_HISTORY.exists():
        try:
            data = json.loads(SIM_HISTORY.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"version": 1, "entries": []}
    else:
        data = {"version": 1, "entries": []}
    data.setdefault("entries", []).append(entry)
    data["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = SIM_HISTORY.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(SIM_HISTORY)


def simulate(plan: dict, record_history: bool = True) -> dict:
    """Dry-run validation. Returns a risk report; does NOT invoke agents."""
    nodes = plan.get("nodes") or []
    edges = plan.get("edges") or []
    risks: list[str] = []

    # 1. Basic shape
    if not nodes:
        risks.append("empty DAG — no nodes to execute")
        return {"risk": "high", "issues": risks, "topo": []}
    if not all("id" in n and "capability" in n for n in nodes):
        risks.append("every node must have an 'id' and 'capability'")

    # 2. Topological order (detects cycles)
    try:
        order = _topo_sort(nodes, edges)
    except ValueError as e:
        risks.append(f"DAG structural error: {e}")
        order = []

    # 3. Depth
    max_depth = len(order)
    if max_depth > 5:
        risks.append(f"DAG depth {max_depth} exceeds max_recursion_depth=5")

    # 4. Capability coverage
    reg = {}
    if REGISTRY.exists():
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    unresolved = [n["id"] for n in nodes if not _capability_resolvable(n.get("capability", ""), reg)]
    if unresolved:
        risks.append(f"no agent covers capabilities for nodes: {unresolved}")

    # 5. Duplicate node ids
    ids = [n["id"] for n in nodes]
    if len(set(ids)) != len(ids):
        risks.append("duplicate node ids in DAG")

    level = "none" if not risks else ("medium" if max_depth <= 5 and "cycle" not in "".join(risks) else "high")
    report = {
        "risk": level,
        "issues": risks,
        "topo": order,
        "node_count": len(nodes),
        "dag_hash": _dag_hash(plan),
    }

    # v3: record every simulation in memory/simulation_history.json so the
    # planner can avoid reproducing the same failing DAG shape.
    if record_history:
        _append_simulation_history({
            "task_id": plan.get("task_id"),
            "task_type": plan.get("task_type"),
            "dag_hash": report["dag_hash"],
            "risk": report["risk"],
            "issues": report["issues"],
            "node_count": report["node_count"],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })
    return report


def should_replan(completed_uncertainties: list[float], threshold: float = 0.5) -> tuple[bool, float]:
    """
    v3: at a replan checkpoint, decide whether to re-invoke the planner.
    Returns (should_replan, aggregate_uncertainty).
    """
    if not completed_uncertainties:
        return False, 0.0
    agg = aggregate_uncertainty(completed_uncertainties)
    return agg >= float(threshold), agg


# ─── Circuit breaker + recording ─────────────────────────────────────────────

class CircuitBreaker:
    """Session-scoped; trips after N identical failures on the same (agent, error-hash)."""

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self.counts: dict[tuple[str, str], int] = {}
        self.tripped: set[str] = set()

    @staticmethod
    def err_hash(error: str) -> str:
        return hashlib.sha256((error or "").encode("utf-8")).hexdigest()[:12]

    def record_failure(self, agent: str, error: str) -> bool:
        """Return True iff this failure trips the breaker for this agent."""
        h = self.err_hash(error)
        key = (agent, h)
        self.counts[key] = self.counts.get(key, 0) + 1
        if self.counts[key] >= self.threshold:
            self.tripped.add(agent)
            return True
        return False

    def is_tripped(self, agent: str) -> bool:
        return agent in self.tripped


def _append_trace(entry: dict) -> None:
    TRACES.parent.mkdir(parents=True, exist_ok=True)
    if TRACES.exists():
        try:
            data = json.loads(TRACES.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"version": 1, "traces": []}
    else:
        data = {"version": 1, "traces": []}
    data.setdefault("traces", []).append(entry)
    tmp = TRACES.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(TRACES)


def record_invocation(task_id: str, node: dict, agent: str, duration_ms: int,
                      tokens: int, success: bool, accuracy: float = 0.0,
                      error: str | None = None, caller: str | None = None,
                      context: dict | None = None) -> dict:
    """
    Called by the orchestrator (or a harness wrapper) around each subagent invocation.
    Writes a trace entry + a scoring record.
    """
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "task_id":    task_id,
        "started_at": started,
        "agents_used": [agent],
        "decisions": [{
            "at":     "execution_engine",
            "node":   node.get("id"),
            "chose":  agent,
            "why":    node.get("rationale") or "selector decision",
        }],
        "durations_ms": {agent: int(duration_ms)},
        "tokens":       {agent: int(tokens)},
        "context_ref":  context_hash(context) if context else None,
        "failures":     [{"agent": agent, "reason": error}] if error else [],
        "success":      bool(success),
    }
    _append_trace(entry)
    score_record(
        agent=agent,
        task_id=task_id,
        duration_ms=int(duration_ms),
        tokens=int(tokens),
        accuracy=float(accuracy),
        success=bool(success),
        caller=caller,
    )
    return entry


# ─── Orchestration helpers ───────────────────────────────────────────────────

def plan_next_step(plan: dict, completed: set[str]) -> dict | None:
    """Return the next node whose predecessors are all in `completed`, or None."""
    nodes = {n["id"]: n for n in plan.get("nodes", [])}
    edges = plan.get("edges") or []
    preds: dict[str, set[str]] = {nid: set() for nid in nodes}
    for src, dst in edges:
        if dst in preds:
            preds[dst].add(src)
    for nid, node in nodes.items():
        if nid in completed:
            continue
        if preds[nid].issubset(completed):
            return node
    return None


def escalation_payload(task_id: str, reason: str, attempted: list[str],
                       last_error: str, suggested: str) -> dict:
    return {
        "kind":     "escalation",
        "task_id":  task_id,
        "payload": {
            "reason":           reason,
            "attempted_agents": attempted,
            "last_error":       last_error,
            "suggested_action": suggested,
            "blocking":         True,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

def _trivial_plan() -> dict:
    return {
        "task_id": f"t-{int(time.time())}",
        "goal":    "smoke test",
        "nodes":   [{"id": "n1", "capability": "noop", "input": {}, "expected_output": "ok"}],
        "edges":   [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="validate environment without running anything")
    parser.add_argument("--simulate", action="store_true", help="simulate a plan (DAG validation)")
    parser.add_argument("--plan", type=str, help="plan as a JSON string")
    parser.add_argument("--plan-file", type=Path, help="plan JSON file")
    args = parser.parse_args(argv)

    if args.dry_run and not args.simulate:
        # Just prove imports + paths work.
        print(json.dumps({
            "ok": True,
            "imports": ["context_engine", "scoring_engine", "agent_selector"],
            "paths_exist": {
                "traces": TRACES.exists(),
                "registry": REGISTRY.exists(),
            },
        }, indent=2))
        return 0

    if args.simulate:
        if args.plan:
            plan = json.loads(args.plan)
        elif args.plan_file:
            plan = json.loads(args.plan_file.read_text(encoding="utf-8"))
        else:
            plan = _trivial_plan()
        report = simulate(plan)
        print(json.dumps(report, indent=2))
        return 0 if report["risk"] == "none" else 1

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
