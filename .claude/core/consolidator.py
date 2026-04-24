#!/usr/bin/env python3
"""
consolidator.py \u2014 periodic wiki + graph + memory maintenance pass.

Bounds growth:
    * Near-duplicate concept files (keyword-TFIDF sim >= 0.90) \u2192 flag for merge.
    * Graph edges with last_updated > DECAY_AGE_DAYS AND confidence < DECAY_CONFIDENCE
      \u2192 decay further; drop if confidence < DROP_THRESHOLD.
    * Verbose concept summaries (> 5 sentences) \u2192 flag for reflection rewrite.
    * Stale simulation_history entries older than PURGE_AGE_DAYS \u2192 remove.
    * Weak trust_matrix pairs (n < 2 AND stale) \u2192 prune.

All actions go to memory/consolidation_log.json. **Never** deletes wiki/raw/.

Usage (CLI):
    python consolidator.py --dry-run            # report only
    python consolidator.py --apply              # execute (destructive for graph/memory state)
    python consolidator.py --apply --prune-only # skip merge flags; just graph/memory cleanup

Stdlib only. Reads representations.py (keyword-tfidf) for concept similarity.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # .claude/
WIKI = ROOT / "wiki"
MEMORY = ROOT / "memory"
GRAPH = WIKI / "graph" / "graph.json"
SIM_HISTORY = MEMORY / "simulation_history.json"
TRUST = MEMORY / "trust_matrix.json"
CONSOLIDATION_LOG = MEMORY / "consolidation_log.json"

DECAY_AGE_DAYS = 90
DECAY_CONFIDENCE = 0.4
DECAY_STEP = 0.05
DROP_THRESHOLD = 0.2
PURGE_AGE_DAYS = 180
WEAK_TRUST_N_THRESHOLD = 2
WEAK_TRUST_AGE_DAYS = 30
NEAR_DUPLICATE_THRESHOLD = 0.90
VERBOSE_SUMMARY_SENTENCES = 5

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _age_days(iso_string: str | None) -> float:
    if not iso_string:
        return 1e9
    try:
        t = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    except ValueError:
        return 1e9
    return max(0.0, (datetime.now(timezone.utc) - t).total_seconds() / 86400.0)


def _load(path: Path, default: dict) -> dict:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return dict(default)


def _save_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    tmp.replace(path)


def _concept_first_paragraph(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    # Skip headings/contradiction warnings; take first non-empty prose block.
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    for block in blocks:
        if not block.startswith("#") and not block.startswith(">"):
            return block
    return ""


def _count_sentences(text: str) -> int:
    return len(re.findall(r"[\.\!\?]+\s", text))


def find_near_duplicate_concepts() -> list[dict]:
    """Uses keyword-tfidf similarity to find concept pairs >= NEAR_DUPLICATE_THRESHOLD."""
    try:
        # Force keyword-tfidf for this pass regardless of env var.
        os.environ["AGENTIC_OS_EMBEDDING_BACKEND"] = "keyword-tfidf"
        from representations import embed, similarity  # noqa: WPS433
    except ImportError:
        return []

    concepts_dir = WIKI / "concepts"
    if not concepts_dir.exists():
        return []

    files = sorted(p for p in concepts_dir.glob("*.md"))
    # Compute embeddings once per file.
    vecs: dict[str, list[float]] = {}
    for p in files:
        vecs[p.stem] = embed(_concept_first_paragraph(p))

    pairs: list[dict] = []
    stems = list(vecs.keys())
    for i, a in enumerate(stems):
        for b in stems[i + 1:]:
            sim = similarity(vecs[a], vecs[b])
            if sim >= NEAR_DUPLICATE_THRESHOLD:
                pairs.append({"a": a, "b": b, "similarity": sim})
    return pairs


def find_verbose_summaries() -> list[dict]:
    """Concept files whose first prose block exceeds VERBOSE_SUMMARY_SENTENCES."""
    out: list[dict] = []
    for domain in ("concepts", "strategies", "experience", "goals", "self", "patterns"):
        d = WIKI / domain
        if not d.exists():
            continue
        for p in d.glob("*.md"):
            if p.name.lower().startswith("readme"):
                continue
            para = _concept_first_paragraph(p)
            n = _count_sentences(para)
            if n > VERBOSE_SUMMARY_SENTENCES:
                out.append({"file": str(p.relative_to(ROOT)), "sentences": n})
    return out


def decay_graph_edges(apply_changes: bool) -> dict:
    graph = _load(GRAPH, {"version": 1, "nodes": [], "indexes": {}})
    decayed = 0
    dropped = 0
    for node in graph.get("nodes", []):
        rels = node.get("relationships", []) or []
        new_rels = []
        for r in rels:
            age = _age_days(r.get("last_updated"))
            conf = float(r.get("confidence", 1.0))
            if age > DECAY_AGE_DAYS and conf < DECAY_CONFIDENCE:
                new_conf = conf - DECAY_STEP
                decayed += 1
                if new_conf < DROP_THRESHOLD:
                    dropped += 1
                    continue  # drop
                r["confidence"] = round(new_conf, 3)
            new_rels.append(r)
        node["relationships"] = new_rels

    if apply_changes and (decayed or dropped):
        _save_atomic(GRAPH, graph)
    return {"decayed_edges": decayed, "dropped_edges": dropped}


def purge_simulation_history(apply_changes: bool) -> dict:
    data = _load(SIM_HISTORY, {"version": 1, "entries": []})
    entries = data.get("entries", []) or []
    before = len(entries)
    kept = [e for e in entries if _age_days(e.get("timestamp")) <= PURGE_AGE_DAYS]
    purged = before - len(kept)
    if apply_changes and purged:
        data["entries"] = kept
        data["updated_at"] = _now_iso()
        _save_atomic(SIM_HISTORY, data)
    return {"simulation_entries_purged": purged, "remaining": len(kept)}


def prune_weak_trust_pairs(apply_changes: bool) -> dict:
    data = _load(TRUST, {"pairs": {}})
    pairs = data.get("pairs", {}) or {}
    before = len(pairs)
    kept = {}
    for key, stats in pairs.items():
        if not isinstance(stats, dict):
            continue
        n = int(stats.get("n", 0))
        age = _age_days(stats.get("updated"))
        if n < WEAK_TRUST_N_THRESHOLD and age > WEAK_TRUST_AGE_DAYS:
            continue  # prune
        kept[key] = stats
    pruned = before - len(kept)
    if apply_changes and pruned:
        data["pairs"] = kept
        data["updated_at"] = _now_iso()
        _save_atomic(TRUST, data)
    return {"trust_pairs_pruned": pruned, "remaining": len(kept)}


def _append_log(entry: dict) -> None:
    data = _load(CONSOLIDATION_LOG, {"version": 1, "entries": []})
    data.setdefault("entries", []).append(entry)
    data["updated_at"] = _now_iso()
    _save_atomic(CONSOLIDATION_LOG, data)


def run(apply_changes: bool, prune_only: bool) -> dict:
    near_dupes: list[dict] = [] if prune_only else find_near_duplicate_concepts()
    verbose:   list[dict] = [] if prune_only else find_verbose_summaries()
    graph_report = decay_graph_edges(apply_changes)
    sim_report = purge_simulation_history(apply_changes)
    trust_report = prune_weak_trust_pairs(apply_changes)

    report = {
        "dry_run":              not apply_changes,
        "near_duplicate_candidates": near_dupes,
        "verbose_summaries":         verbose,
        "graph":                graph_report,
        "simulation_history":   sim_report,
        "trust_matrix":         trust_report,
        "timestamp":            _now_iso(),
    }
    if apply_changes:
        _append_log({
            "kind": "consolidation_pass",
            "summary": {
                "near_duplicate_candidates": len(near_dupes),
                "verbose_summaries":         len(verbose),
                "decayed_edges":             graph_report.get("decayed_edges", 0),
                "dropped_edges":             graph_report.get("dropped_edges", 0),
                "simulation_entries_purged": sim_report.get("simulation_entries_purged", 0),
                "trust_pairs_pruned":        trust_report.get("trust_pairs_pruned", 0),
            },
            "timestamp": _now_iso(),
        })
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="report only; no writes")
    parser.add_argument("--apply", action="store_true", help="execute (destructive)")
    parser.add_argument("--prune-only", action="store_true", help="skip merge/verbose detection; just cleanup")
    args = parser.parse_args(argv)

    apply_changes = args.apply and not args.dry_run
    if not args.apply and not args.dry_run:
        args.dry_run = True

    report = run(apply_changes=apply_changes, prune_only=args.prune_only)
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
