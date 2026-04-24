#!/usr/bin/env python3
"""
reward.py \u2014 task-level reward signal for goal-driven optimisation.

A single deterministic function that maps (success, cost, risk) to a scalar
reward in [-1.0, 1.0]. Used by goal_keeper after every task completion to
update `current_goal.cumulative_reward` and to surface trends.

Default formulation:

    reward = clip(w_s * success - w_c * cost - w_r * risk, -1, 1)

Default weights: (1.0, 0.3, 0.5).
Inputs are floats in [0, 1]:
    success \u2014 evaluator's task-level success score
    cost    \u2014 normalised cost (1.0 = budget exhausted)
    risk    \u2014 aggregate risk classification (low=0.0, medium=0.4, high=0.7, critical=1.0)

Usage (CLI):
    python reward.py --success 0.9 --cost 0.1 --risk 0.0
    python reward.py --success 0.5 --cost 0.2 --risk 0.4 --weights 1.0,0.5,0.5
    python reward.py --classify-risk medium     # convenience: returns the float

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys

DEFAULT_WEIGHTS = (1.0, 0.3, 0.5)

RISK_TO_FLOAT = {
    "low":      0.0,
    "medium":   0.4,
    "high":     0.7,
    "critical": 1.0,
}


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def reward(success: float, cost: float, risk: float,
           weights: tuple[float, float, float] | None = None) -> float:
    """Return a scalar reward in [-1, 1]."""
    w_s, w_c, w_r = weights if weights is not None else DEFAULT_WEIGHTS
    s = max(0.0, min(1.0, float(success)))
    c = max(0.0, min(1.0, float(cost)))
    r = max(0.0, min(1.0, float(risk)))
    raw = w_s * s - w_c * c - w_r * r
    return round(_clip(raw), 4)


def classify_risk(label: str) -> float:
    return RISK_TO_FLOAT.get(label, 0.5)


def _parse_weights(s: str) -> tuple[float, float, float]:
    parts = [float(x) for x in s.split(",")]
    if len(parts) != 3:
        raise ValueError("--weights expects three comma-separated floats: w_success,w_cost,w_risk")
    return parts[0], parts[1], parts[2]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--success", type=float)
    parser.add_argument("--cost", type=float)
    parser.add_argument("--risk", type=float)
    parser.add_argument("--weights", type=str, default=None,
                        help="comma-separated w_success,w_cost,w_risk (default 1.0,0.3,0.5)")
    parser.add_argument("--classify-risk", choices=list(RISK_TO_FLOAT.keys()),
                        help="convenience: print the float for a risk label")
    args = parser.parse_args(argv)

    if args.classify_risk:
        print(json.dumps({"label": args.classify_risk, "value": classify_risk(args.classify_risk)}, indent=2))
        return 0

    if args.success is None or args.cost is None or args.risk is None:
        parser.print_help()
        return 2

    weights = _parse_weights(args.weights) if args.weights else DEFAULT_WEIGHTS
    r = reward(args.success, args.cost, args.risk, weights=weights)
    print(json.dumps({
        "success": args.success, "cost": args.cost, "risk": args.risk,
        "weights": weights, "reward": r,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
