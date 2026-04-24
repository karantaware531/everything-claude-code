#!/usr/bin/env python3
"""
reset_test_state.py \u2014 reset leftover smoke-test state from memory/ and optionally wiki/.

Safe by design: defaults to --dry-run; refuses to reset when it detects real
production data. Use this once after the initial bootstrap/self-tests to wipe
the transactional residue that the test_runner + smoke scripts leave behind.

What gets reset (memory/ \u2014 transactional state):
    * budgets.json              \u2192 empty active + history
    * simulation_history.json   \u2192 empty entries
    * world_state.json          \u2192 empty states + transitions
    * environment_state.json    \u2192 empty probe (TTL preserved)

Optionally (--include-wiki-smoke, one-off bootstrap cleanup):
    * remove smoke-test concepts (note, see, overview, overview-langgraph, langgraph-smoke-test)
    * remove .claude/wiki/raw/docs/smoke-test.md
    * remove .claude/wiki/summaries/smoke-test.md
    * rebuild graph.json from remaining concepts

What is NEVER touched:
    * CLAUDE.md, runtime.md, policies/**
    * wiki/raw/** (immutable outside the explicit smoke-test removal above)
    * wiki/strategies/, wiki/experience/, wiki/goals/, wiki/self/, wiki/patterns/, wiki/consensus/
    * registry.json
    * logs.json, agent_history.json, trust_matrix.json, goals_state.json, system_profile.json
    * forecasts.json, consolidation_log.json, corpus_df.json

Usage:
    python reset_test_state.py --dry-run                   (default; preview only)
    python reset_test_state.py --apply                     (reset memory state only)
    python reset_test_state.py --apply --include-wiki-smoke (also drop smoke concepts)
    python reset_test_state.py --apply --force             (override safety refusal)

Exit codes:
    0 \u2014 success (dry-run or applied)
    1 \u2014 refused because real data detected (use --force to override)
    2 \u2014 usage error
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
MEMORY = ROOT / "memory"
WIKI = ROOT / "wiki"

# Files to reset (path \u2192 empty payload).
RESETS: dict[Path, dict] = {
    MEMORY / "budgets.json": {
        "version": 1, "updated_at": None, "active": {}, "history": []
    },
    MEMORY / "simulation_history.json": {
        "version": 1, "updated_at": None, "entries": []
    },
    MEMORY / "world_state.json": {
        "version": 1, "updated_at": None, "states": {}, "transitions": []
    },
    MEMORY / "environment_state.json": {
        "version": 1, "probed_at": None, "ttl_seconds": 300,
        "tools": {}, "shell_dependencies": {}, "recent_failures": {}, "wall_clock": None,
    },
}

# Smoke-test concept slugs created during bootstrap smoke tests.
SMOKE_CONCEPT_SLUGS = {
    "note", "see", "overview", "overview-langgraph", "langgraph-smoke-test",
    "langgraph", "langchain", "dag", "framework", "multi", "agent",
    "crewai", "autogen",
}

# Raw + summary files tied to the bootstrap smoke test.
SMOKE_RAW_FILES = [
    WIKI / "raw" / "docs" / "smoke-test.md",
]
SMOKE_SUMMARY_FILES = [
    WIKI / "summaries" / "smoke-test.md",
]

# Task-ID patterns considered known smoke-test values.
SMOKE_TASK_IDS = {"t-smoke", "t-test-runner-smoke"}


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# -----------------------------------------------------------------------------
# Safety checks \u2014 refuse to reset if real data is present.
# -----------------------------------------------------------------------------

def _real_data_signals() -> list[str]:
    """Return a list of reasons to refuse; empty means safe to reset."""
    reasons: list[str] = []

    # system_profile.json \u2014 if any epoch has run, real learning has happened.
    profile = _load(MEMORY / "system_profile.json", {"epoch_count": 0})
    if int(profile.get("epoch_count", 0)) > 0:
        reasons.append(
            f"system_profile.json has epoch_count={profile.get('epoch_count')} "
            f"(real epoch_learner runs present)"
        )

    # simulation_history \u2014 more than 10 entries or any with non-smoke task_id.
    sim = _load(MEMORY / "simulation_history.json", {"entries": []})
    sim_entries = sim.get("entries", []) or []
    if len(sim_entries) > 10:
        reasons.append(f"simulation_history.json has {len(sim_entries)} entries (> 10)")
    for entry in sim_entries:
        tid = entry.get("task_id")
        if tid and tid not in SMOKE_TASK_IDS:
            reasons.append(f"simulation_history.json has non-smoke task_id: {tid!r}")
            break

    # budgets.json history \u2014 any task_id outside SMOKE_TASK_IDS is real usage.
    budgets = _load(MEMORY / "budgets.json", {"active": {}, "history": []})
    for task_id in (budgets.get("active", {}) or {}).keys():
        if task_id not in SMOKE_TASK_IDS:
            reasons.append(f"budgets.json has active task_id: {task_id!r}")
    for entry in (budgets.get("history", []) or []):
        tid = entry.get("task_id")
        if tid and tid not in SMOKE_TASK_IDS:
            reasons.append(f"budgets.json has non-smoke history task_id: {tid!r}")
            break

    # trust_matrix \u2014 any real pair entry.
    trust = _load(MEMORY / "trust_matrix.json", {"pairs": {}})
    if trust.get("pairs"):
        reasons.append(f"trust_matrix.json has {len(trust['pairs'])} pair(s) \u2014 real invocations recorded")

    # agent_history \u2014 any real agent invocation with a non-smoke task_id.
    history = _load(MEMORY / "agent_history.json", {"entries": []})
    real_history = [
        e for e in history.get("entries", []) or []
        if e.get("task_id") and e["task_id"] not in SMOKE_TASK_IDS
    ]
    if real_history:
        reasons.append(
            f"agent_history.json has {len(real_history)} entry/entries with non-smoke task_ids"
        )

    # logs.json \u2014 any real task logged.
    logs = _load(MEMORY / "logs.json", {"entries": []})
    if logs.get("entries"):
        reasons.append(f"logs.json has {len(logs['entries'])} entry/entries \u2014 real tasks logged")

    return reasons


# -----------------------------------------------------------------------------
# Reset operations.
# -----------------------------------------------------------------------------

def plan_memory_reset() -> dict:
    """Report what the memory reset would change."""
    changes: list[dict] = []
    for path, payload in RESETS.items():
        current = _load(path, payload)
        same = json.dumps(current, sort_keys=True) == json.dumps(payload, sort_keys=True)
        changes.append({
            "path":     str(path.relative_to(ROOT.parent)) if ROOT.parent in path.parents else str(path),
            "action":   "reset" if not same else "no-op",
            "bytes_before": path.stat().st_size if path.exists() else 0,
        })
    return {"files": changes}


def plan_wiki_cleanup() -> dict:
    """Report what the wiki smoke cleanup would remove."""
    concepts_to_remove: list[str] = []
    for slug in sorted(SMOKE_CONCEPT_SLUGS):
        candidate = WIKI / "concepts" / f"{slug}.md"
        if candidate.exists():
            concepts_to_remove.append(str(candidate.relative_to(ROOT.parent)))
    raws = [str(p.relative_to(ROOT.parent)) for p in SMOKE_RAW_FILES if p.exists()]
    summaries = [str(p.relative_to(ROOT.parent)) for p in SMOKE_SUMMARY_FILES if p.exists()]
    return {
        "concepts_to_remove":  concepts_to_remove,
        "raw_files_to_remove": raws,
        "summary_files_to_remove": summaries,
        "graph_rebuild_needed": bool(concepts_to_remove or raws),
    }


def apply_memory_reset() -> dict:
    out: list[dict] = []
    for path, payload in RESETS.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
        tmp.replace(path)
        out.append({"path": str(path.relative_to(ROOT.parent)), "reset_at": _now_iso()})
    return {"reset": out}


def apply_wiki_cleanup() -> dict:
    removed: list[str] = []
    for slug in SMOKE_CONCEPT_SLUGS:
        candidate = WIKI / "concepts" / f"{slug}.md"
        if candidate.exists():
            candidate.unlink()
            removed.append(str(candidate.relative_to(ROOT.parent)))
    for p in SMOKE_RAW_FILES + SMOKE_SUMMARY_FILES:
        if p.exists():
            p.unlink()
            removed.append(str(p.relative_to(ROOT.parent)))

    # Reset graph.json \u2014 it referenced the deleted concepts.
    graph = WIKI / "graph" / "graph.json"
    graph_payload = {
        "version": 1, "updated_at": None, "nodes": [],
        "indexes": {"by_entity": {}, "by_type": {}, "adjacency": {}},
    }
    graph.parent.mkdir(parents=True, exist_ok=True)
    tmp = graph.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(graph_payload, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    tmp.replace(graph)

    return {"removed": removed, "graph_reset": True}


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", default=None,
                        help="preview changes only (default when neither --dry-run nor --apply is given)")
    parser.add_argument("--apply", action="store_true", help="actually reset")
    parser.add_argument("--include-wiki-smoke", action="store_true",
                        help="also remove smoke-test concepts + raw/summary; rebuild graph.json")
    parser.add_argument("--force", action="store_true",
                        help="override the safety refusal (use with care; real data will be wiped)")
    args = parser.parse_args(argv)

    # Default to dry-run if no mode specified.
    if args.dry_run is None and not args.apply:
        args.dry_run = True
    if args.dry_run and args.apply:
        print("ERROR: --dry-run and --apply are mutually exclusive", file=sys.stderr)
        return 2

    report: dict = {
        "mode":              "dry-run" if args.dry_run else "apply",
        "include_wiki_smoke": bool(args.include_wiki_smoke),
        "memory_plan":        plan_memory_reset(),
    }
    if args.include_wiki_smoke:
        report["wiki_plan"] = plan_wiki_cleanup()

    # Safety check before any apply.
    if args.apply:
        reasons = _real_data_signals()
        if reasons and not args.force:
            print(json.dumps({
                "refused":  True,
                "reason":   "real data detected; refusing to reset without --force",
                "signals":  reasons,
                "hint":     "review the signals above; pass --force only if you really mean to wipe real state",
            }, indent=2))
            return 1

        report["memory_result"] = apply_memory_reset()
        if args.include_wiki_smoke:
            report["wiki_result"] = apply_wiki_cleanup()

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
