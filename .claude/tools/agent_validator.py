#!/usr/bin/env python3
"""
agent_validator.py — validates agent specs and checks registry for duplicates.

Usage:
    python agent_validator.py --spec <spec.json>
        Validates a single spec file against the schema. Exit 0 on success.

    python agent_validator.py --similarity "<verb-phrase>" [--spec <spec.json>]
        Returns the registry entry with the highest Jaccard similarity and the score.
        Exits 0 if similarity < 0.7 (safe to create), 2 if >= 0.7 (reuse).

    python agent_validator.py --self-test
        Validates every agent currently in registry.json. Exit 0 if all pass.

Schema v2 (enforced):
    {
      "name":             <str, snake_case, unique>,
      "role":             <str, one-line>,             # v2
      "layer":            <"cognitive|execution|governance|meta">,   # v2
      "version":          <int, >= 1>,                  # v2
      "capabilities":     [<str>, ...]   (>= 1),
      "inputs":           [<str>, ...],
      "outputs":          [<str>, ...],
      "tools":            [<str>, ...],
      "constraints":      [<str>, ...],
      "evaluation_metrics": [<str>, ...],               # v2
      "protocol_version": "1.0",                        # v2
      "source":           "seed|factory"
    }

v2 fields are REQUIRED for entries with source="factory", and RECOMMENDED for seeds.
Validator accepts v1-only entries (no layer/role/etc.) for backward compat on `seed`;
rejects them for `factory`.

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REGISTRY = ROOT / "registry.json"  # v5.2: moved from wiki/

REQUIRED_KEYS = ("name", "capabilities", "inputs", "outputs", "tools", "constraints")
V2_REQUIRED_KEYS = ("role", "layer", "version", "evaluation_metrics", "protocol_version")
ALL_LIST_KEYS = ("capabilities", "inputs", "outputs", "tools", "constraints", "evaluation_metrics")
NAME_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
VALID_LAYERS = {"cognitive", "execution", "governance", "meta"}

SIMILARITY_REUSE_THRESHOLD = 0.7


def _load_registry() -> dict[str, Any]:
    if not REGISTRY.exists():
        return {"agents": [], "version": 1}
    with REGISTRY.open("r", encoding="utf-8") as f:
        return json.load(f)


def _tokens(text: str) -> set[str]:
    """Lowercase word tokens, min length 2, for Jaccard."""
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 2}


def _capability_tokens(caps: list[str]) -> set[str]:
    out: set[str] = set()
    for c in caps:
        out.update(_tokens(c))
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def validate_spec(spec: dict[str, Any], existing_names: set[str] | None = None) -> list[str]:
    """
    Return a list of error strings; empty list == valid.
    For source='factory', all v2 fields are required.
    For source='seed' (or missing), v2 fields are optional but validated if present.
    """
    errors: list[str] = []
    existing_names = existing_names or set()
    source = spec.get("source", "seed")

    for key in REQUIRED_KEYS:
        if key not in spec:
            errors.append(f"missing required key: {key}")

    if source == "factory":
        for key in V2_REQUIRED_KEYS:
            if key not in spec:
                errors.append(f"missing required v2 key for factory-source agent: {key}")

    if errors:
        return errors  # bail early, downstream checks assume keys exist

    name = spec["name"]
    if not isinstance(name, str):
        errors.append("name must be a string")
    elif not NAME_RE.match(name):
        errors.append(f"name '{name}' must match ^[a-z][a-z0-9_]{{1,63}}$")
    elif name in existing_names:
        errors.append(f"name '{name}' already exists in registry")

    # v2 field validation (if present)
    if "layer" in spec:
        if spec["layer"] not in VALID_LAYERS:
            errors.append(f"layer must be one of {sorted(VALID_LAYERS)}; got '{spec['layer']}'")
    if "version" in spec:
        if not isinstance(spec["version"], int) or spec["version"] < 1:
            errors.append(f"version must be an int >= 1; got {spec['version']!r}")
    if "role" in spec and not isinstance(spec["role"], str):
        errors.append("role must be a string")
    if "protocol_version" in spec and spec["protocol_version"] != "1.0":
        errors.append(f"protocol_version must be '1.0'; got '{spec['protocol_version']}'")

    # List-type fields (union of v1 and v2, but only validate keys that exist)
    for key in ALL_LIST_KEYS:
        if key not in spec:
            continue
        val = spec[key]
        if not isinstance(val, list):
            errors.append(f"{key} must be a list")
            continue
        for i, item in enumerate(val):
            if not isinstance(item, str):
                errors.append(f"{key}[{i}] must be a string")

    if isinstance(spec.get("capabilities"), list) and len(spec["capabilities"]) < 1:
        errors.append("capabilities must contain at least one entry")

    # Factory-source agents need at least 'accuracy' and 'success_rate' in metrics
    if source == "factory" and isinstance(spec.get("evaluation_metrics"), list):
        metrics = set(spec["evaluation_metrics"])
        missing = {"accuracy", "success_rate"} - metrics
        if missing:
            errors.append(f"factory-source agent missing required evaluation_metrics: {sorted(missing)}")

    return errors


def best_similarity(target_capability_text: str, registry: dict[str, Any]) -> tuple[str | None, float]:
    """Return (agent_name, score) with the highest Jaccard on capability tokens."""
    target_tokens = _tokens(target_capability_text)
    best_name: str | None = None
    best_score = 0.0
    for agent in registry.get("agents", []):
        score = jaccard(target_tokens, _capability_tokens(agent.get("capabilities", [])))
        if score > best_score:
            best_name = agent.get("name")
            best_score = score
    return best_name, best_score


def cmd_spec(spec_path: Path) -> int:
    with spec_path.open("r", encoding="utf-8") as f:
        spec = json.load(f)
    registry = _load_registry()
    existing = {a["name"] for a in registry.get("agents", [])}
    errors = validate_spec(spec, existing)
    if errors:
        print("INVALID spec:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"OK: spec for '{spec['name']}' is valid.")
    return 0


def cmd_similarity(phrase: str) -> int:
    registry = _load_registry()
    name, score = best_similarity(phrase, registry)
    result = {
        "query": phrase,
        "best_match": name,
        "score": round(score, 3),
        "decision": "reuse" if score >= SIMILARITY_REUSE_THRESHOLD else "create_ok",
    }
    print(json.dumps(result, indent=2))
    return 2 if score >= SIMILARITY_REUSE_THRESHOLD else 0


def cmd_self_test() -> int:
    registry = _load_registry()
    agents = registry.get("agents", [])
    if not agents:
        print("registry.json has no agents; nothing to validate.")
        return 0

    seen_names: set[str] = set()
    any_fail = False
    for i, agent in enumerate(agents):
        # validate against all previously-seen names to catch duplicates
        errors = validate_spec(agent, seen_names)
        if errors:
            any_fail = True
            print(f"FAIL [{i}] {agent.get('name', '?')}:", file=sys.stderr)
            for e in errors:
                print(f"  - {e}", file=sys.stderr)
        else:
            print(f"OK   [{i}] {agent['name']}")
            seen_names.add(agent["name"])
    return 1 if any_fail else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--spec", type=Path, help="path to a spec JSON to validate")
    parser.add_argument("--similarity", type=str, help="capability phrase to search for")
    parser.add_argument("--self-test", action="store_true", help="validate every agent in registry.json")
    args = parser.parse_args(argv)

    if args.self_test:
        return cmd_self_test()
    if args.similarity:
        return cmd_similarity(args.similarity)
    if args.spec:
        return cmd_spec(args.spec)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
