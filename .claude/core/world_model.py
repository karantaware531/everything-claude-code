#!/usr/bin/env python3
"""
world_model.py \u2014 symbolic state-transition table for action prediction.

Honest scope: this is symbolic case-based reasoning (CBR), not neural prediction.
The interface is right; the backend is intentionally simple.

State + action -> probable next state(s) with confidence. Built from observation:
each successful (action -> outcome) pair updates the table; confidence grows with
repeated identical observations and decays with contradicting ones.

Usage (CLI):
    python world_model.py --observe <state> <action> <next_state>
    python world_model.py --predict <state> <action>
    python world_model.py --stats

Persists to .claude/memory/world_state.json.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
WORLD = ROOT / "memory" / "world_state.json"

DEFAULT_CONFIDENCE_GAIN = 0.10
MIN_CONFIDENCE = 0.05


def _load() -> dict:
    if not WORLD.exists():
        return {"version": 1, "updated_at": None, "states": {}, "transitions": []}
    try:
        return json.loads(WORLD.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 1, "updated_at": None, "states": {}, "transitions": []}


def _save(world: dict) -> None:
    WORLD.parent.mkdir(parents=True, exist_ok=True)
    world["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tmp = WORLD.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(world, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(WORLD)


def _ensure_state(world: dict, state: str) -> None:
    if state not in world["states"]:
        world["states"][state] = {"description": state, "observed_count": 0,
                                  "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    world["states"][state]["observed_count"] += 1


def observe(state: str, action: str, next_state: str) -> dict:
    """Record an observation: (state, action) led to next_state."""
    world = _load()
    _ensure_state(world, state)
    _ensure_state(world, next_state)

    # Find existing transition or create one
    found = None
    for t in world["transitions"]:
        if t["from"] == state and t["action"] == action and t["to"] == next_state:
            found = t
            break

    if found:
        found["n"] += 1
        found["confidence"] = min(1.0, float(found["confidence"]) + DEFAULT_CONFIDENCE_GAIN)
        found["last_seen"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        world["transitions"].append({
            "from":       state,
            "action":     action,
            "to":         next_state,
            "n":          1,
            "confidence": DEFAULT_CONFIDENCE_GAIN,
            "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_seen":  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        })

    # Mild penalty for any *other* known transition from same (state, action) \u2014
    # the world is showing it's not deterministic.
    for t in world["transitions"]:
        if t["from"] == state and t["action"] == action and t["to"] != next_state:
            t["confidence"] = max(MIN_CONFIDENCE,
                                  float(t["confidence"]) - DEFAULT_CONFIDENCE_GAIN / 2)

    _save(world)
    return {"recorded": True, "from": state, "action": action, "to": next_state,
            "transitions_for_pair": [t for t in world["transitions"]
                                     if t["from"] == state and t["action"] == action]}


def predict(state: str, action: str) -> dict:
    """
    Given current state + proposed action, return predicted next state(s)
    sorted by confidence.
    """
    world = _load()
    candidates = [t for t in world["transitions"] if t["from"] == state and t["action"] == action]
    if not candidates:
        return {
            "from":       state,
            "action":     action,
            "predictions": [],
            "note":       "no prior observation \u2014 outcome unknown",
        }
    # Sort by confidence desc, then n desc.
    candidates_sorted = sorted(candidates, key=lambda t: (t["confidence"], t["n"]), reverse=True)
    return {
        "from":       state,
        "action":     action,
        "predictions": [
            {"to": t["to"], "confidence": round(float(t["confidence"]), 3), "n": t["n"]}
            for t in candidates_sorted
        ],
    }


def scenarios(state: str, action: str) -> dict:
    """
    v5: return best / expected / worst case predictions for (state, action).

    * best     = highest-confidence prediction (what usually succeeds)
    * expected = confidence-weighted expectation over observed outcomes
    * worst    = lowest-confidence or known-bad outcome (used by risk assessment)
    """
    world = _load()
    candidates = [t for t in world["transitions"] if t["from"] == state and t["action"] == action]
    if not candidates:
        return {
            "from":     state,
            "action":   action,
            "best":     None,
            "expected": None,
            "worst":    None,
            "note":     "no prior observation \u2014 outcome unknown",
        }

    sorted_by_conf = sorted(candidates, key=lambda t: float(t["confidence"]), reverse=True)
    best = sorted_by_conf[0]
    worst = sorted_by_conf[-1]

    # Expected: pick the outcome with highest (confidence * n) product.
    def _weight(t: dict) -> float:
        return float(t["confidence"]) * float(t.get("n", 1))
    expected = max(candidates, key=_weight)

    return {
        "from":   state,
        "action": action,
        "best": {
            "to":         best["to"],
            "confidence": round(float(best["confidence"]), 3),
            "n":          best["n"],
            "reasoning":  "highest observed confidence for this pair",
        },
        "expected": {
            "to":         expected["to"],
            "confidence": round(float(expected["confidence"]), 3),
            "n":          expected["n"],
            "reasoning":  "confidence-weighted by observation count",
        },
        "worst": {
            "to":         worst["to"],
            "confidence": round(float(worst["confidence"]), 3),
            "n":          worst["n"],
            "reasoning":  "lowest-confidence outcome \u2014 consider for risk planning",
        },
    }


def stats() -> dict:
    world = _load()
    return {
        "total_states":      len(world.get("states", {})),
        "total_transitions": len(world.get("transitions", [])),
        "updated_at":        world.get("updated_at"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--observe", nargs=3, metavar=("STATE", "ACTION", "NEXT"))
    group.add_argument("--predict", nargs=2, metavar=("STATE", "ACTION"))
    group.add_argument("--scenarios", nargs=2, metavar=("STATE", "ACTION"),
                       help="v5: return best/expected/worst case predictions")
    group.add_argument("--stats", action="store_true")
    args = parser.parse_args(argv)

    if args.observe:
        s, a, n = args.observe
        print(json.dumps(observe(s, a, n), indent=2))
        return 0
    if args.predict:
        s, a = args.predict
        print(json.dumps(predict(s, a), indent=2))
        return 0
    if args.scenarios:
        s, a = args.scenarios
        print(json.dumps(scenarios(s, a), indent=2))
        return 0
    if args.stats:
        print(json.dumps(stats(), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
