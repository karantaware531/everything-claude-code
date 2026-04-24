#!/usr/bin/env python3
"""
utility.py \u2014 expected-utility reasoning for decision-making under uncertainty.

v5 decision-theory primitive. Given:
    p_success    probability the action/plan succeeds (0..1)
    reward       expected reward if it succeeds (from reward.py, already in [-1, 1])
    risk_cost    expected loss if it fails (0..1, from risk classification)

Returns:
    expected_utility = p_success * reward - (1 - p_success) * risk_cost

Used by:
    * agent_selector \u2014 tie-break when top candidates' scores are within 0.05
    * planner / strategy_explorer \u2014 pick the highest-utility candidate DAG
    * meta_controller \u2014 sanity check: if utility < 0 across plausible paths, tier up

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys

DEFAULT_WEIGHTS = (1.0, 1.0)  # (w_reward, w_risk)


def _clip(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def utility(p_success: float, reward: float, risk_cost: float,
            weights: tuple[float, float] | None = None) -> float:
    """
    Expected utility. Returns a float in [-1, 1] (assuming reward and risk_cost are each in [-1, 1]).

    Formula:
        EU = w_r * p * reward - w_rc * (1 - p) * risk_cost

    Interpretation:
        EU > 0  \u2014 action is worth taking
        EU \u2248 0  \u2014 marginal; depends on tie-break rules
        EU < 0  \u2014 expected loss; prefer inaction or an alternative
    """
    w_r, w_rc = weights if weights is not None else DEFAULT_WEIGHTS
    p = max(0.0, min(1.0, float(p_success)))
    r = float(reward)
    rc = max(0.0, min(1.0, float(risk_cost)))
    eu = w_r * p * r - w_rc * (1.0 - p) * rc
    return round(_clip(eu), 4)


def probability_from_uncertainty(uncertainty: float) -> float:
    """Convert evaluator uncertainty (0..1) into p_success. Simple inverse."""
    return round(1.0 - max(0.0, min(1.0, float(uncertainty))), 4)


def risk_cost_from_label(label: str) -> float:
    """Map a risk label into a risk_cost in [0, 1]."""
    return {"low": 0.1, "medium": 0.4, "high": 0.7, "critical": 1.0}.get(label, 0.5)


def compare(candidates: list[dict]) -> list[dict]:
    """
    Rank a list of `{name, p_success, reward, risk_cost}` dicts by utility, desc.
    Returns the same dicts annotated with `utility` plus a `rank` index.
    """
    scored = []
    for c in candidates:
        u = utility(c.get("p_success", 0.7),
                    c.get("reward", 0.0),
                    c.get("risk_cost", 0.4),
                    c.get("weights"))
        scored.append({**c, "utility": u})
    scored.sort(key=lambda d: d["utility"], reverse=True)
    for rank, d in enumerate(scored):
        d["rank"] = rank
    return scored


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--p-success", type=float, help="probability of success in [0, 1]")
    parser.add_argument("--reward", type=float, help="expected reward in [-1, 1]")
    parser.add_argument("--risk-cost", type=float, help="expected loss if fail in [0, 1]")
    parser.add_argument("--weights", type=str, default=None,
                        help="comma-separated w_reward,w_risk (default 1.0,1.0)")
    parser.add_argument("--from-uncertainty", type=float, default=None,
                        help="derive p_success from uncertainty instead of --p-success")
    parser.add_argument("--from-risk-label", type=str, default=None,
                        help="derive risk_cost from {low,medium,high,critical}")
    args = parser.parse_args(argv)

    p = args.p_success
    if args.from_uncertainty is not None:
        p = probability_from_uncertainty(args.from_uncertainty)
    rc = args.risk_cost
    if args.from_risk_label is not None:
        rc = risk_cost_from_label(args.from_risk_label)

    if p is None or args.reward is None or rc is None:
        parser.print_help()
        return 2

    weights = None
    if args.weights:
        parts = [float(x) for x in args.weights.split(",")]
        if len(parts) != 2:
            print("ERROR: --weights expects two floats", file=sys.stderr)
            return 2
        weights = (parts[0], parts[1])

    eu = utility(p, args.reward, rc, weights)
    print(json.dumps({
        "p_success":  p,
        "reward":     args.reward,
        "risk_cost":  rc,
        "weights":    list(weights) if weights else list(DEFAULT_WEIGHTS),
        "utility":    eu,
        "verdict":    "positive" if eu > 0 else ("neutral" if eu == 0 else "negative"),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
