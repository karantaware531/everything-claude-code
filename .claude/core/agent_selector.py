#!/usr/bin/env python3
"""
agent_selector.py — score-based routing with ε-greedy exploration.

    score(agent, task) = w_sem  · semantic_match
                       + w_succ · success_rate
                       + w_cost · cost_efficiency
                       + w_trust · pair_trust   (if caller is known)

Weights come from `.claude/policies/config.yaml`.
ε-greedy: with probability ε (default 0.1), pick a random qualifying *cold-start*
agent (n < min_trials) instead of the top-scored one. Prevents cold-starve.

Usage (CLI):
    python agent_selector.py --capability "plan a task" --task "build a DAG for X"
    python agent_selector.py --capability "..." --task "..." --caller orchestrator

Usage (library):
    from agent_selector import select, score_all

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

# Reuse scoring + config loading by importing sibling modules at runtime.
ROOT = Path(__file__).resolve().parents[1]  # .claude/
REGISTRY = ROOT / "registry.json"  # v5.2: moved from wiki/
CONFIG = ROOT / "policies" / "config.yaml"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scoring_engine import stats as score_stats, trust_stats  # noqa: E402
from utility import utility as expected_utility  # noqa: E402

UTILITY_TIE_BREAK_WINDOW = 0.05  # v5: if top-2 scores differ by < this, break ties via utility

# ─── Config loading (minimal YAML parser, copied from policy_guard) ──────────

def _strip_inline_comment(line: str) -> str:
    """Drop '# comment' from end of a YAML line, but not inside quotes."""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            # Only treat as comment if preceded by whitespace (or at start).
            if i == 0 or line[i - 1].isspace():
                return line[:i].rstrip()
    return line


def _parse_yaml(text: str) -> Any:
    lines = [_strip_inline_comment(ln).rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    idx = 0

    def parse_scalar(s: str) -> Any:
        s = s.strip()
        if not s:
            return None
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        if s.startswith("'") and s.endswith("'"):
            return s[1:-1]
        low = s.lower()
        if low in ("true", "yes"):
            return True
        if low in ("false", "no"):
            return False
        if low in ("null", "~"):
            return None
        try:
            return int(s)
        except ValueError:
            pass
        try:
            return float(s)
        except ValueError:
            pass
        return s

    def parse_block(base_indent: int) -> Any:
        nonlocal idx
        if idx >= len(lines):
            return None
        first = lines[idx]
        first_indent = len(first) - len(first.lstrip())
        if first_indent < base_indent:
            return None
        stripped = first.lstrip()
        if stripped.startswith("- "):
            out_list: list[Any] = []
            while idx < len(lines):
                ln = lines[idx]
                ind = len(ln) - len(ln.lstrip())
                if ind < base_indent:
                    break
                s = ln.lstrip()
                if not s.startswith("- "):
                    break
                item = s[2:].strip()
                idx += 1
                if item.startswith("[") and item.endswith("]"):
                    out_list.append([parse_scalar(x) for x in item[1:-1].split(",") if x.strip()])
                elif ":" in item and not (item.startswith('"') or item.startswith("'")):
                    k, _, v = item.partition(":")
                    entry = {k.strip(): parse_scalar(v)}
                    if idx < len(lines):
                        next_ln = lines[idx]
                        next_indent = len(next_ln) - len(next_ln.lstrip())
                        next_stripped = next_ln.lstrip()
                        if next_indent > base_indent and not next_stripped.startswith("- "):
                            cont = parse_block(next_indent)
                            if isinstance(cont, dict):
                                entry.update(cont)
                    out_list.append(entry)
                else:
                    out_list.append(parse_scalar(item))
            return out_list
        out_map: dict[str, Any] = {}
        while idx < len(lines):
            ln = lines[idx]
            ind = len(ln) - len(ln.lstrip())
            if ind < base_indent or ind > base_indent:
                break
            s = ln.lstrip()
            if ":" not in s:
                break
            key, _, rest = s.partition(":")
            key, rest = key.strip(), rest.strip()
            idx += 1
            if rest == "":
                sub = parse_block(base_indent + 2)
                out_map[key] = sub
            elif rest.startswith("[") and rest.endswith("]"):
                inner = rest[1:-1]
                out_map[key] = [parse_scalar(x) for x in inner.split(",") if x.strip()]
            else:
                out_map[key] = parse_scalar(rest)
        return out_map

    return parse_block(0) or {}


_CONFIG_CACHE: dict | None = None


def load_config() -> dict:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    if not CONFIG.exists():
        _CONFIG_CACHE = {}
        return _CONFIG_CACHE
    _CONFIG_CACHE = _parse_yaml(CONFIG.read_text(encoding="utf-8")) or {}
    return _CONFIG_CACHE


def _weights() -> dict:
    cfg = load_config()
    sel = (cfg.get("selector") or {}).get("weights") or {}
    return {
        "semantic":         float(sel.get("semantic", 0.5)),
        "success_rate":     float(sel.get("success_rate", 0.3)),
        "cost_efficiency":  float(sel.get("cost_efficiency", 0.2)),
        "pair_trust":       float(sel.get("pair_trust", 0.1)),
    }


def _epsilon_and_mintrials() -> tuple[float, int]:
    cfg = load_config()
    sel = (cfg.get("selector") or {}).get("exploration") or {}
    return float(sel.get("epsilon", 0.10)), int(sel.get("min_trials", 5))


def _no_match_threshold() -> float:
    cfg = load_config()
    sel = cfg.get("selector") or {}
    return float(sel.get("no_match_threshold", 0.30))


# ─── Semantic match ───────────────────────────────────────────────────────────

def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 2}


def _semantic_match(agent: dict, capability: str, task: str) -> float:
    agent_text = " ".join([
        agent.get("role", ""),
        " ".join(agent.get("capabilities", [])),
    ])
    query = f"{capability} {task}"
    return len(_tokens(agent_text) & _tokens(query)) / max(1, len(_tokens(agent_text) | _tokens(query)))


# ─── Scoring ─────────────────────────────────────────────────────────────────

def score_all(capability: str, task: str, caller: str | None = None) -> list[dict]:
    if not REGISTRY.exists():
        return []
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    agents = reg.get("agents", []) or []
    w = _weights()
    scored: list[dict] = []
    for agent in agents:
        sem = _semantic_match(agent, capability, task)
        stat = score_stats(agent["name"])
        trust_pair = trust_stats(caller, agent["name"]) if caller else {"pass_rate": 0.7, "default": True}

        score = (
            w["semantic"]        * sem
            + w["success_rate"]  * float(stat["success_rate"])
            + w["cost_efficiency"] * float(stat["cost_efficiency"])
            + w["pair_trust"]    * float(trust_pair.get("pass_rate", 0.7))
        )
        scored.append({
            "agent": agent["name"],
            "layer": agent.get("layer"),
            "score": round(score, 4),
            "breakdown": {
                "semantic":        round(sem, 3),
                "success_rate":    float(stat["success_rate"]),
                "cost_efficiency": float(stat["cost_efficiency"]),
                "pair_trust":      round(float(trust_pair.get("pass_rate", 0.7)), 3),
                "n_trials":        int(stat["n"]),
                "trust_default":   trust_pair.get("default", True),
            },
        })
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored


def select(capability: str, task: str, caller: str | None = None,
           rng: random.Random | None = None) -> dict:
    """
    Returns a decision dict:
        {"chosen": <name or None>, "score": float, "rationale": str, "alternatives": [...]}
    If the top score is below no_match_threshold, chosen=None → caller should factory-handoff.
    """
    scored = score_all(capability, task, caller)
    if not scored:
        return {"chosen": None, "score": 0.0, "rationale": "empty registry", "alternatives": []}

    eps, min_trials = _epsilon_and_mintrials()
    threshold = _no_match_threshold()
    rng = rng or random.Random()

    cold = [r for r in scored if r["breakdown"]["n_trials"] < min_trials]

    # ε-greedy: with probability eps, pick a random cold-start (if any).
    if cold and rng.random() < eps:
        chosen = rng.choice(cold)
        rationale = f"exploration (eps={eps}): random cold-start pick from {len(cold)} candidates"
    else:
        chosen = scored[0]
        rationale = f"top-scored ({chosen['score']})"
        # v5: utility tie-break. If runner-up is within the tie-break window, compare EU.
        if len(scored) >= 2 and (scored[0]["score"] - scored[1]["score"]) < UTILITY_TIE_BREAK_WINDOW:
            def _eu(entry: dict) -> float:
                br = entry.get("breakdown", {})
                p = float(br.get("success_rate", 0.7))
                reward_proxy = float(br.get("semantic", 0.0))        # approx; better signal than 0
                risk_cost = 1.0 - float(br.get("cost_efficiency", 1.0))
                return expected_utility(p, reward_proxy, max(0.0, risk_cost))
            eu_first = _eu(scored[0])
            eu_second = _eu(scored[1])
            if eu_second > eu_first + 0.01:
                chosen = scored[1]
                rationale = (f"tie-break via utility: runner-up EU={eu_second:.3f} > top EU={eu_first:.3f} "
                             f"within tie window {UTILITY_TIE_BREAK_WINDOW}")

    if chosen["score"] < threshold and not (cold and rng.random() < 0):  # deterministic threshold
        return {
            "chosen": None,
            "score": chosen["score"],
            "rationale": f"best score {chosen['score']} below threshold {threshold} → factory handoff",
            "alternatives": scored[:3],
        }

    return {
        "chosen": chosen["agent"],
        "layer":  chosen["layer"],
        "score":  chosen["score"],
        "rationale": rationale,
        "breakdown": chosen["breakdown"],
        "alternatives": [r for r in scored[1:4]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capability", required=True, help="verb-phrase describing the needed capability")
    parser.add_argument("--task", required=True, help="full task text for semantic matching")
    parser.add_argument("--caller", type=str, default=None, help="name of the calling agent (for trust)")
    parser.add_argument("--all", action="store_true", help="print all scored agents instead of just the chosen one")
    parser.add_argument("--seed", type=int, default=None, help="deterministic RNG seed (for testing)")
    args = parser.parse_args(argv)

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    if args.all:
        print(json.dumps(score_all(args.capability, args.task, args.caller), indent=2))
        return 0

    decision = select(args.capability, args.task, args.caller, rng)
    print(json.dumps(decision, indent=2))
    return 0 if decision.get("chosen") else 1


if __name__ == "__main__":
    sys.exit(main())
