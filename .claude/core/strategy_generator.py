#!/usr/bin/env python3
"""
strategy_generator.py \u2014 produce K candidate DAGs for a task; rank by expected utility.

Deliberative planning primitive for v5. Given a task description (and an
existing coarse DAG from the planner, if available), generate K variants:

    Variant 1 \u2014 baseline (planner's first pick)
    Variant 2 \u2014 alternate agent assignments (substitute by semantic similarity)
    Variant 3 \u2014 alternate decomposition depth (coarser or finer)

Simulate each via execution_engine.simulate() (risk check, no real execution).
Score each via utility.utility() using approximated p_success / reward / risk_cost.
Return candidates ranked by utility.

Usage (CLI):
    python strategy_generator.py --task "add feature X" --k 3
    python strategy_generator.py --task "..." --k 3 --simulate

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REGISTRY = ROOT / "registry.json"  # v5.2: moved from wiki/
WORKFLOWS = ROOT / "workflows"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from utility import utility as expected_utility  # noqa: E402
from execution_engine import simulate as simulate_dag, _dag_hash  # noqa: E402
from agent_selector import score_all  # noqa: E402


def _load_registry() -> dict:
    if not REGISTRY.exists():
        return {"agents": []}
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _agents_by_layer() -> dict:
    reg = _load_registry()
    out: dict[str, list[dict]] = {}
    for a in reg.get("agents", []):
        out.setdefault(a.get("layer", "unknown"), []).append(a)
    return out


def _baseline_dag(task: str, task_id: str | None = None) -> dict:
    """
    Baseline: research \u2192 code \u2192 critic \u2192 evaluator. Matches the codegen workflow.
    """
    return {
        "task_id": task_id or "t-strat-1",
        "goal":    task,
        "nodes": [
            {"id": "n1", "capability": "decompose task into DAG", "input": {"task": task}, "expected_output": "refined_dag: json", "assigned_agent": "decomposer", "retries_allowed": 1},
            {"id": "n2", "capability": "write source code", "input": {"task": task}, "expected_output": "changed_files: list", "assigned_agent": "code_agent", "retries_allowed": 2},
            {"id": "n3", "capability": "red-team agent output", "input": {"agent_output": "<from n2>"}, "expected_output": "critique: json", "assigned_agent": "critic", "retries_allowed": 1},
            {"id": "n4", "capability": "check correctness of agent output", "input": {"agent_output": "<from n2>"}, "expected_output": "verdict: json", "assigned_agent": "evaluator", "retries_allowed": 0},
        ],
        "edges": [["n1", "n2"], ["n2", "n3"], ["n3", "n4"]],
    }


def _alternate_assignments(base: dict, task: str) -> dict:
    """
    Variant 2: for each node, try an alternate agent scored by semantic similarity.
    Leaves the structure identical; only swaps assigned_agent where a plausible alt exists.
    """
    variant = json.loads(json.dumps(base))  # deep copy
    variant["task_id"] = (base.get("task_id") or "t-strat") + "-alt"
    for node in variant.get("nodes", []):
        cap = node.get("capability", "")
        # Ask the selector for all candidates; pick the 2nd-highest (if any) as a variant.
        ranked = score_all(cap, task)
        if len(ranked) >= 2 and ranked[1]["score"] > 0.15:
            current = node.get("assigned_agent")
            alt = ranked[1]["agent"]
            if alt and alt != current:
                node["assigned_agent"] = alt
    return variant


def _coarser_dag(task: str) -> dict:
    """Variant 3: collapse decomposer into planner, drop critic. Faster but riskier."""
    return {
        "task_id": "t-strat-coarse",
        "goal":    task,
        "nodes": [
            {"id": "n1", "capability": "decompose task into DAG", "input": {"task": task}, "expected_output": "dag: json", "assigned_agent": "planner", "retries_allowed": 0},
            {"id": "n2", "capability": "write source code", "input": {"task": task}, "expected_output": "changed_files: list", "assigned_agent": "code_agent", "retries_allowed": 1},
            {"id": "n3", "capability": "check correctness of agent output", "input": {"agent_output": "<from n2>"}, "expected_output": "verdict: json", "assigned_agent": "evaluator", "retries_allowed": 0},
        ],
        "edges": [["n1", "n2"], ["n2", "n3"]],
    }


def _finer_dag(task: str) -> dict:
    """Variant: add research_agent up front and reflection at the end. Slower but thorough."""
    return {
        "task_id": "t-strat-fine",
        "goal":    task,
        "nodes": [
            {"id": "n1", "capability": "mine repository for information", "input": {"question": task}, "expected_output": "findings: list", "assigned_agent": "research_agent", "retries_allowed": 1},
            {"id": "n2", "capability": "decompose task into DAG", "input": {"task": task}, "expected_output": "refined_dag: json", "assigned_agent": "decomposer", "retries_allowed": 1},
            {"id": "n3", "capability": "write source code", "input": {"task": task}, "expected_output": "changed_files: list", "assigned_agent": "code_agent", "retries_allowed": 2},
            {"id": "n4", "capability": "red-team agent output", "input": {"agent_output": "<from n3>"}, "expected_output": "critique: json", "assigned_agent": "critic", "retries_allowed": 1},
            {"id": "n5", "capability": "check correctness of agent output", "input": {"agent_output": "<from n3>"}, "expected_output": "verdict: json", "assigned_agent": "evaluator", "retries_allowed": 0},
            {"id": "n6", "capability": "distill lesson into wiki experience", "input": {"trace": "<from run>"}, "expected_output": "reflection_report: json", "assigned_agent": "reflection", "retries_allowed": 0},
        ],
        "edges": [["n1", "n2"], ["n2", "n3"], ["n3", "n4"], ["n4", "n5"], ["n5", "n6"]],
    }


def _estimate_utility(dag: dict, risk_report: dict) -> dict:
    """Approximate utility signals from DAG shape + simulation report."""
    node_count = len(dag.get("nodes", []))
    risk = risk_report.get("risk", "high")
    # Heuristic p_success: more nodes => more points of failure, but capped.
    p_success = max(0.3, min(0.95, 1.0 - 0.07 * max(0, node_count - 3)))
    # Reward heuristic: finer DAGs reward more thoroughness (~0.5-0.8).
    reward = min(0.9, 0.5 + 0.05 * node_count)
    # Risk cost from simulation verdict.
    risk_cost = {"none": 0.1, "medium": 0.4, "high": 0.8}.get(risk, 0.5)
    eu = expected_utility(p_success, reward, risk_cost)
    return {"p_success": p_success, "reward": reward, "risk_cost": risk_cost, "utility": eu}


def generate(task: str, k: int = 3, run_simulation: bool = True) -> list[dict]:
    """Return a list of candidate plans with utility scores, ranked desc."""
    builders = [_baseline_dag, lambda t: _alternate_assignments(_baseline_dag(t), t),
                _coarser_dag, _finer_dag]
    candidates: list[dict] = []
    for i, builder in enumerate(builders):
        if len(candidates) >= k:
            break
        try:
            dag = builder(task)
        except Exception as e:  # noqa: BLE001
            candidates.append({"error": f"builder {i} failed: {e}"})
            continue
        risk_report = simulate_dag(dag, record_history=False) if run_simulation else {"risk": "unknown"}
        util = _estimate_utility(dag, risk_report)
        candidates.append({
            "variant_id":  f"v{i+1}",
            "dag":         dag,
            "dag_hash":    _dag_hash(dag),
            "simulation":  risk_report,
            **util,
        })

    candidates.sort(key=lambda c: c.get("utility", -1.0), reverse=True)
    for rank, c in enumerate(candidates):
        c["rank"] = rank
    return candidates[:k]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", required=True, help="task description (short)")
    parser.add_argument("--k", type=int, default=3, help="how many candidates to generate")
    parser.add_argument("--simulate", action="store_true", help="run execution_engine.simulate() on each candidate")
    parser.add_argument("--compact", action="store_true", help="omit full DAG bodies; show only summary")
    args = parser.parse_args(argv)

    results = generate(args.task, k=args.k, run_simulation=args.simulate)

    if args.compact:
        compact = []
        for r in results:
            compact.append({
                "variant_id": r.get("variant_id"),
                "rank":       r.get("rank"),
                "dag_hash":   r.get("dag_hash"),
                "node_count": len(r.get("dag", {}).get("nodes", [])),
                "utility":    r.get("utility"),
                "risk":       (r.get("simulation", {}) or {}).get("risk"),
            })
        print(json.dumps({"count": len(compact), "candidates": compact}, indent=2))
    else:
        print(json.dumps({"count": len(results), "candidates": results}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
