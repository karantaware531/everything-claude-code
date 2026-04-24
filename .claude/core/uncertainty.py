#!/usr/bin/env python3
"""
uncertainty.py \u2014 epistemic uncertainty primitives for Agentic OS v3.

Distinguishes two quantities that v2's evaluator conflated:
    * score       \u2014 point estimate of correctness (0.0\u20131.0, higher = more correct)
    * uncertainty \u2014 spread of plausible outcomes (0.0\u20131.0, higher = less certain)

Low score + low uncertainty = "confidently wrong".
High score + high uncertainty = "optimistically correct, but brittle".
Only low-uncertainty high-score outputs should be trusted autonomously.

This module provides three pure functions:

    aggregate(uncertainties)           \u2192 DAG-level roll-up
    propagate(parent_u, child_u)       \u2192 edge-level combination
    classify(u)                        \u2192 categorical level (low/medium/high/critical)

Thresholds come from .claude/policies/config.yaml (selector.uncertainty_thresholds).

Usage (CLI):
    python uncertainty.py --aggregate 0.1,0.3,0.2
    python uncertainty.py --propagate 0.2 0.4
    python uncertainty.py --classify 0.75

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]  # .claude/
CONFIG = ROOT / "policies" / "config.yaml"

# Fallback thresholds when config.yaml is absent/malformed.
DEFAULT_THRESHOLDS = {"low": 0.20, "medium": 0.50, "high": 0.80}

# Aggregation decay factor: each additional high-uncertainty node adds a
# fraction of its uncertainty on top of the running max, capped at 1.0.
AGGREGATION_DECAY = 0.30


def _load_thresholds() -> dict:
    if not CONFIG.exists():
        return dict(DEFAULT_THRESHOLDS)
    # Avoid circular import with agent_selector's YAML parser \u2014 inline a minimal
    # block finder just for this one key path.
    try:
        text = CONFIG.read_text(encoding="utf-8")
    except OSError:
        return dict(DEFAULT_THRESHOLDS)
    thresholds = dict(DEFAULT_THRESHOLDS)
    in_selector = False
    in_uncertainty = False
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            continue
        indent = len(stripped) - len(stripped.lstrip())
        body = stripped.strip()
        if indent == 0:
            in_selector = body.startswith("selector:")
            in_uncertainty = False
            continue
        if not in_selector:
            continue
        if body.startswith("uncertainty_thresholds:"):
            in_uncertainty = True
            continue
        if in_uncertainty and indent > 2:
            if ":" in body:
                key, _, value = body.partition(":")
                key = key.strip()
                value = value.split("#", 1)[0].strip()
                try:
                    thresholds[key] = float(value)
                except ValueError:
                    pass
        elif in_uncertainty and indent <= 2:
            in_uncertainty = False
    return thresholds


def aggregate(uncertainties: Iterable[float]) -> float:
    """
    Combine per-node uncertainties into a DAG-level summary.

    Strategy: the maximum dominates (a single highly-uncertain node poisons the
    plan), but each additional uncertain node adds a fraction via decayed sum.

    Returns a value clamped to [0, 1].
    """
    vals = [max(0.0, min(1.0, float(u))) for u in uncertainties]
    if not vals:
        return 0.0
    vals_sorted = sorted(vals, reverse=True)
    result = vals_sorted[0]
    for u in vals_sorted[1:]:
        result = min(1.0, result + AGGREGATION_DECAY * u * (1.0 - result))
    return round(result, 4)


def propagate(parent_u: float, child_u: float) -> float:
    """
    Combine two uncertainties along an edge (producer \u2192 consumer).

    Probabilistic OR: assuming independence of uncertainty sources,
    combined = 1 - (1 - parent) * (1 - child).

    This is the same formula as failure probability in a series circuit, which
    is the right intuition: the chain is only as certain as its weakest link.
    """
    p = max(0.0, min(1.0, float(parent_u)))
    c = max(0.0, min(1.0, float(child_u)))
    return round(1.0 - (1.0 - p) * (1.0 - c), 4)


def classify(u: float, thresholds: dict | None = None) -> str:
    """Return one of: 'low', 'medium', 'high', 'critical'."""
    t = thresholds or _load_thresholds()
    u = max(0.0, min(1.0, float(u)))
    if u < t.get("low", DEFAULT_THRESHOLDS["low"]):
        return "low"
    if u < t.get("medium", DEFAULT_THRESHOLDS["medium"]):
        return "medium"
    if u < t.get("high", DEFAULT_THRESHOLDS["high"]):
        return "high"
    return "critical"


def _parse_floats(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--aggregate", metavar="LIST", help="comma-separated uncertainties")
    group.add_argument("--propagate", metavar=("PARENT", "CHILD"), nargs=2, type=float)
    group.add_argument("--classify", metavar="U", type=float)
    parser.add_argument("--with-thresholds", action="store_true",
                        help="print the thresholds used")
    args = parser.parse_args(argv)

    if args.aggregate:
        vals = _parse_floats(args.aggregate)
        result = aggregate(vals)
        out = {"input": vals, "aggregate": result, "class": classify(result)}
        if args.with_thresholds:
            out["thresholds"] = _load_thresholds()
        print(json.dumps(out, indent=2))
        return 0

    if args.propagate:
        p, c = args.propagate
        result = propagate(p, c)
        print(json.dumps({"parent": p, "child": c, "propagated": result,
                          "class": classify(result)}, indent=2))
        return 0

    if args.classify is not None:
        result = classify(args.classify)
        print(json.dumps({"uncertainty": args.classify, "class": result,
                          "thresholds": _load_thresholds() if args.with_thresholds else None}, indent=2))
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
