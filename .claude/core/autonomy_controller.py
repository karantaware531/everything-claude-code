#!/usr/bin/env python3
"""
autonomy_controller.py \u2014 decide how much autonomy the system should exercise.

v3's core meta-cognitive primitive. Given aggregate uncertainty + risk + recent
failure signals, return a tier 1\u20134:

    1  autonomous           \u2014 v2 default execution
    2  notify               \u2014 execute but surface every decision
    3  approval_required    \u2014 pause before any write/shell action
    4  policy_amendment     \u2014 always stop for user

The controller composes signals:

    base_tier      = uncertainty_to_tier[classify(uncertainty)]
    risk_bumped    = base_tier + risk_bumps[risk]
    failure_bumped = risk_bumped + (1 if recent_failure_rate >= 0.5 else 0)
    final          = min(4, max(1, failure_bumped))

Parameters come from .claude/policies/config.yaml (autonomy.*).

Usage (CLI):
    python autonomy_controller.py --task "deploy X" --uncertainty 0.3 --risk low
    python autonomy_controller.py --task "..." --uncertainty 0.8 --risk high --recent-fail-rate 0.6

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
CONFIG = ROOT / "policies" / "config.yaml"
GOVERNANCE = ROOT / "policies" / "governance.yaml"
DOMAIN_POLICIES = ROOT / "policies" / "domain_policies.yaml"

# Inline local imports (avoid sys.path manipulation).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uncertainty import classify as classify_uncertainty  # noqa: E402

TIER_NAMES = {1: "autonomous", 2: "notify", 3: "approval_required", 4: "policy_amendment"}

DEFAULTS = {
    "default_tier": 1,
    "uncertainty_to_tier": {"low": 1, "medium": 2, "high": 3, "critical": 4},
    "risk_bumps":          {"low": 0, "medium": 1, "high": 2},
}


def _read_lines_stripped(path: Path) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.rstrip()
        # strip inline comments respecting quotes (cheap; we control the YAML)
        if "#" in line:
            out.append((indent, line.split("#", 1)[0].rstrip()))
        else:
            out.append((indent, line))
    return out


def load_autonomy_config() -> dict:
    """Minimal, purpose-built YAML reader for the autonomy section of config.yaml."""
    cfg = {
        "default_tier":       DEFAULTS["default_tier"],
        "uncertainty_to_tier": dict(DEFAULTS["uncertainty_to_tier"]),
        "risk_bumps":          dict(DEFAULTS["risk_bumps"]),
    }
    if not CONFIG.exists():
        return cfg

    lines = _read_lines_stripped(CONFIG)
    in_autonomy = False
    in_utt = False
    in_rb = False

    for indent, body in lines:
        body_stripped = body.lstrip()
        if indent == 0:
            in_autonomy = body_stripped.startswith("autonomy:")
            in_utt = in_rb = False
            continue
        if not in_autonomy:
            continue

        if indent == 2:
            in_utt = body_stripped.startswith("uncertainty_to_tier:")
            in_rb  = body_stripped.startswith("risk_bumps:")
            if body_stripped.startswith("default_tier:"):
                val = body_stripped.split(":", 1)[1].strip()
                try:
                    cfg["default_tier"] = int(val)
                except ValueError:
                    pass
            continue

        if indent >= 4:
            if ":" not in body_stripped:
                continue
            key, _, value = body_stripped.partition(":")
            key, value = key.strip(), value.strip()
            try:
                value_i = int(value)
            except ValueError:
                continue
            if in_utt:
                cfg["uncertainty_to_tier"][key] = value_i
            elif in_rb:
                cfg["risk_bumps"][key] = value_i

    return cfg


def _load_domain_policies() -> dict:
    """Minimal parser for domain_policies.yaml — returns {'domain': {'min_tier': int, 'tier_bumps': {...}}}."""
    if not DOMAIN_POLICIES.exists():
        return {}
    text = DOMAIN_POLICIES.read_text(encoding="utf-8")
    out: dict = {}
    in_policies = False
    current_domain: str | None = None
    in_bumps = False
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        line = raw.rstrip()
        if "#" in line:
            line = line.split("#", 1)[0].rstrip()
        indent = len(raw) - len(raw.lstrip())
        body = line.strip()
        if indent == 0:
            in_policies = body.startswith("domain_policies:")
            current_domain = None
            in_bumps = False
            continue
        if not in_policies:
            continue
        if indent == 2 and body.endswith(":"):
            current_domain = body.rstrip(":").strip()
            out[current_domain] = {"min_tier": 1, "tier_bumps": {}}
            in_bumps = False
            continue
        if current_domain is None:
            continue
        if indent == 4:
            if body.startswith("min_tier:"):
                try:
                    out[current_domain]["min_tier"] = int(body.split(":", 1)[1].strip())
                except ValueError:
                    pass
                in_bumps = False
            elif body.startswith("tier_bumps:"):
                in_bumps = True
                rest = body.split(":", 1)[1].strip()
                if rest.startswith("{") and rest.endswith("}"):
                    out[current_domain]["tier_bumps"] = {}
                    in_bumps = False
            else:
                in_bumps = False
        elif indent >= 6 and in_bumps and ":" in body:
            k, _, v = body.partition(":")
            try:
                out[current_domain]["tier_bumps"][k.strip()] = int(v.strip())
            except ValueError:
                pass
    return out


def decide_tier(uncertainty: float, risk: str = "low",
                recent_failure_rate: float = 0.0,
                cfg: dict | None = None,
                domain: str | None = None) -> dict:
    """
    Core decision. Returns a dict with tier, name, and the signal breakdown.

    v5: optional `domain` applies per-task-type adjustments from
    `policies/domain_policies.yaml` (e.g. codegen bumps on high uncertainty;
    security_sensitive clamps to tier >= 3).
    """
    cfg = cfg or load_autonomy_config()
    u_class = classify_uncertainty(uncertainty)

    base = cfg["uncertainty_to_tier"].get(u_class, cfg["default_tier"])
    risk_bump = cfg["risk_bumps"].get(risk, 0)
    failure_bump = 1 if recent_failure_rate >= 0.5 else 0
    raw = base + risk_bump + failure_bump

    # v5: apply domain policy.
    domain_info: dict = {}
    domain_bump = 0
    domain_min = 1
    if domain:
        domain_policies = _load_domain_policies()
        policy = domain_policies.get(domain) or domain_policies.get("default") or {}
        domain_min = int(policy.get("min_tier", 1))
        bumps = policy.get("tier_bumps", {}) or {}
        # Named-condition bumps:
        if u_class == "high" and "uncertainty_high" in bumps:
            domain_bump += int(bumps["uncertainty_high"])
        if u_class == "critical" and "uncertainty_critical" in bumps:
            domain_bump += int(bumps["uncertainty_critical"])
        domain_info = {"applied_policy": domain, "min_tier": domain_min, "bump": domain_bump}

    raw_with_domain = raw + domain_bump
    tier = max(domain_min, max(1, min(4, raw_with_domain)))

    return {
        "tier":              tier,
        "name":              TIER_NAMES[tier],
        "uncertainty":       float(uncertainty),
        "uncertainty_class": u_class,
        "risk":              risk,
        "recent_failure_rate": float(recent_failure_rate),
        "domain":            domain,
        "breakdown": {
            "base_from_uncertainty": base,
            "risk_bump":             risk_bump,
            "failure_bump":          failure_bump,
            "domain_bump":           domain_bump,
            "domain_min_tier":       domain_min,
            "raw_sum":               raw_with_domain,
            "final_tier":            tier,
        },
        "domain_info":       domain_info,
        "requires_user":     tier >= 3,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--task", type=str, required=True, help="short task description (advisory only)")
    parser.add_argument("--uncertainty", type=float, required=True, help="aggregate uncertainty in [0, 1]")
    parser.add_argument("--risk", type=str, default="low", choices=["low", "medium", "high"])
    parser.add_argument("--recent-fail-rate", type=float, default=0.0,
                        help="recent session failure rate in [0, 1]")
    parser.add_argument("--domain", type=str, default=None,
                        help="v5: task_type for domain_policies.yaml lookup "
                             "(e.g. codegen, debug, rag, ingest, security_sensitive)")
    args = parser.parse_args(argv)

    verdict = decide_tier(
        uncertainty=args.uncertainty,
        risk=args.risk,
        recent_failure_rate=args.recent_fail_rate,
        domain=args.domain,
    )
    verdict["task"] = args.task
    print(json.dumps(verdict, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
