#!/usr/bin/env python3
"""
epoch_learner.py \u2014 N-task window analysis; updates system self-profile.

Pulls the most recent `--window` entries from memory/agent_history.json and
memory/logs.json, computes:
    * per-agent success rates and median latency
    * domain-level competence scores (group by task_type if present)
    * weak spots (agents/domains with success_rate < 0.4 over n>=5)
    * strong pairings (caller->callee pass_rate >= 0.85 over n>=3 from trust_matrix)
    * global metrics (total tasks, success rate, avg latency, avg reward)

Updates `memory/system_profile.json` (numerical) and writes a narrative summary
directly to `.claude/notes/self/epoch-<n>.md` (v5.2 Graphify era; graphify
indexes it on next `--update`).

Usage:
    python epoch_learner.py --window 20
    python epoch_learner.py --window 5 --dry-run

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # .claude/
HISTORY = ROOT / "memory" / "agent_history.json"
LOGS = ROOT / "memory" / "logs.json"
TRUST = ROOT / "memory" / "trust_matrix.json"
PROFILE = ROOT / "memory" / "system_profile.json"
NOTES_SELF = ROOT / "notes" / "self"  # v5.2: direct write destination (was wiki/raw/docs/)


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def _atomic_write(path: Path, data: dict | str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    if isinstance(data, str):
        tmp.write_text(data, encoding="utf-8", newline="\n")
    else:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(path)


def analyse(window: int) -> dict:
    history = _load(HISTORY, {"entries": []})
    entries = history.get("entries", [])[-max(1, window):]

    by_agent: dict[str, dict] = {}
    for e in entries:
        a = e.get("agent", "?")
        slot = by_agent.setdefault(a, {"n": 0, "successes": 0, "durations": [], "rewards": []})
        slot["n"] += 1
        if e.get("success"):
            slot["successes"] += 1
        d = e.get("metrics", {}).get("duration_ms")
        if isinstance(d, (int, float)):
            slot["durations"].append(int(d))
        # rewards are post-task; populated by goal_keeper if present in extra
        r = e.get("reward")
        if isinstance(r, (int, float)):
            slot["rewards"].append(float(r))

    competence: dict[str, dict] = {}
    weak_spots: list[dict] = []
    for agent, slot in by_agent.items():
        n = slot["n"] or 1
        sr = slot["successes"] / n
        durs = slot["durations"]
        rew = slot["rewards"]
        competence[agent] = {
            "n":              slot["n"],
            "success_rate":   round(sr, 3),
            "latency_p50_ms": int(statistics.median(durs)) if durs else None,
            "avg_reward":     round(sum(rew) / len(rew), 3) if rew else None,
        }
        if slot["n"] >= 5 and sr < 0.4:
            weak_spots.append({"agent": agent, "n": slot["n"], "success_rate": round(sr, 3)})

    trust = _load(TRUST, {"pairs": {}}).get("pairs", {})
    strong_pairings = []
    for key, stats_dict in (trust or {}).items():
        n = int(stats_dict.get("n", 0))
        pr = float(stats_dict.get("pass_rate", 0.0))
        if n >= 3 and pr >= 0.85:
            strong_pairings.append({"pair": key, "n": n, "pass_rate": round(pr, 3)})

    logs = _load(LOGS, {"entries": []}).get("entries", [])
    total_tasks = len(logs)
    successes = sum(1 for e in logs if e.get("outcome") == "success")
    global_success_rate = successes / total_tasks if total_tasks else None

    all_durations = [d for slot in by_agent.values() for d in slot["durations"]]
    all_rewards = [r for slot in by_agent.values() for r in slot["rewards"]]

    return {
        "window":           window,
        "entries_seen":     len(entries),
        "domain_competence": competence,
        "weak_spots":        weak_spots,
        "strong_pairings":   strong_pairings,
        "global_metrics": {
            "total_tasks":   total_tasks,
            "success_rate":  round(global_success_rate, 3) if global_success_rate is not None else None,
            "avg_latency_ms": int(statistics.mean(all_durations)) if all_durations else None,
            "avg_reward":    round(sum(all_rewards) / len(all_rewards), 3) if all_rewards else None,
        },
    }


def render_narrative(report: dict, epoch_n: int) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# Self-knowledge epoch {epoch_n}",
        "",
        f"Generated: {now}",
        f"Window: last {report['window']} agent invocations ({report['entries_seen']} seen).",
        "",
        "## Global metrics",
        "```json",
        json.dumps(report["global_metrics"], indent=2),
        "```",
        "",
        "## Strong pairings",
    ]
    if report["strong_pairings"]:
        for p in report["strong_pairings"]:
            lines.append(f"- `{p['pair']}` \u2014 pass_rate={p['pass_rate']}, n={p['n']}")
    else:
        lines.append("_(none yet)_")
    lines.append("")
    lines.append("## Weak spots")
    if report["weak_spots"]:
        for w in report["weak_spots"]:
            lines.append(f"- `{w['agent']}` \u2014 success_rate={w['success_rate']}, n={w['n']}")
    else:
        lines.append("_(none over the recent window)_")
    lines.append("")
    lines.append("## Per-agent competence")
    if report["domain_competence"]:
        for agent, stats_dict in sorted(report["domain_competence"].items()):
            lines.append(f"- `{agent}` \u2014 n={stats_dict['n']}, success={stats_dict['success_rate']}, "
                         f"p50={stats_dict['latency_p50_ms']}ms, avg_reward={stats_dict['avg_reward']}")
    else:
        lines.append("_(no entries in window)_")
    lines.append("")
    lines.append("## Recommended self-claims")
    lines.append("_(v5.2: direct write to .claude/notes/self/; run `py -3 -m graphify .claude/notes/ --update` to index)_")
    return "\n".join(lines) + "\n"


def update_profile(report: dict) -> dict:
    profile = _load(PROFILE, {"version": 1, "epoch_count": 0})
    profile["updated_at"]        = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    profile["epoch_count"]       = int(profile.get("epoch_count", 0)) + 1
    profile["domain_competence"] = report["domain_competence"]
    profile["weak_spots"]        = report["weak_spots"]
    profile["strong_pairings"]   = report["strong_pairings"]
    profile["global_metrics"]    = report["global_metrics"]
    return profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--window", type=int, default=20, help="how many recent agent_history entries to analyse")
    parser.add_argument("--dry-run", action="store_true", help="report only; don't write profile or narrative")
    args = parser.parse_args(argv)

    report = analyse(args.window)

    if args.dry_run:
        print(json.dumps({"dry_run": True, "report": report}, indent=2))
        return 0

    profile = update_profile(report)
    _atomic_write(PROFILE, profile)

    epoch_n = profile["epoch_count"]
    narrative_path = NOTES_SELF / f"epoch-{epoch_n:04d}.md"
    _atomic_write(narrative_path, render_narrative(report, epoch_n))

    print(json.dumps({
        "wrote_profile": str(PROFILE),
        "wrote_narrative": str(narrative_path),
        "epoch_count": epoch_n,
        "report": report,
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
