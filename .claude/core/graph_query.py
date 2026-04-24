#!/usr/bin/env python3
"""
graph_query.py — query helper for .claude/wiki/graph/graph.json.

Fast lookups via the indexes block:
    by_entity:  {slug: node_offset}
    by_type:    {type: [node_offset, ...]}
    adjacency:  {slug: [neighbour_slug, ...]}

Usage:
    python graph_query.py --find planner
    python graph_query.py --neighbors planner
    python graph_query.py --neighbors planner --depth 2
    python graph_query.py --by-type agent
    python graph_query.py --stale --older-than-days 30
    python graph_query.py --stats

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
GRAPH = ROOT / "wiki" / "graph" / "graph.json"


def _load() -> dict:
    if not GRAPH.exists():
        return {"version": 1, "nodes": [], "indexes": {"by_entity": {}, "by_type": {}, "adjacency": {}}}
    return json.loads(GRAPH.read_text(encoding="utf-8"))


def find(entity: str) -> dict | None:
    g = _load()
    idx = (g.get("indexes") or {}).get("by_entity") or {}
    off = idx.get(entity)
    if off is None:
        # linear fallback (tiny graphs or missing index)
        for n in g.get("nodes", []):
            if n.get("entity") == entity:
                return n
        return None
    try:
        return g["nodes"][int(off)]
    except (IndexError, KeyError, ValueError, TypeError):
        return None


def neighbors(entity: str, depth: int = 1) -> list[dict]:
    g = _load()
    adj = (g.get("indexes") or {}).get("adjacency") or {}
    seen: set[str] = {entity}
    frontier: list[str] = [entity]
    order: list[str] = []
    for _ in range(max(1, int(depth))):
        next_frontier: list[str] = []
        for e in frontier:
            for nbr in adj.get(e, []) or []:
                if nbr not in seen:
                    seen.add(nbr)
                    next_frontier.append(nbr)
                    order.append(nbr)
        if not next_frontier:
            break
        frontier = next_frontier
    return [find(e) for e in order if find(e)]


def by_type(t: str) -> list[dict]:
    g = _load()
    idx = (g.get("indexes") or {}).get("by_type") or {}
    offs = idx.get(t) or []
    out: list[dict] = []
    for off in offs:
        try:
            out.append(g["nodes"][int(off)])
        except (IndexError, KeyError, ValueError, TypeError):
            continue
    if not out:  # linear fallback
        out = [n for n in g.get("nodes", []) if n.get("type") == t]
    return out


def stale(older_than_days: int) -> list[dict]:
    g = _load()
    now = datetime.now(timezone.utc)
    cutoff_days = int(older_than_days)
    out: list[dict] = []
    for n in g.get("nodes", []):
        ts = n.get("last_updated")
        if not ts:
            continue
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now - t).days >= cutoff_days:
            out.append(n)
    return out


def stats() -> dict:
    g = _load()
    nodes = g.get("nodes", []) or []
    types: dict[str, int] = {}
    edges = 0
    for n in nodes:
        t = n.get("type", "?")
        types[t] = types.get(t, 0) + 1
        edges += len(n.get("relationships", []) or [])
    return {
        "total_nodes": len(nodes),
        "total_edges": edges,
        "by_type":     types,
        "updated_at":  g.get("updated_at"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--find", metavar="ENTITY")
    group.add_argument("--neighbors", metavar="ENTITY")
    group.add_argument("--by-type", metavar="TYPE")
    group.add_argument("--stale", action="store_true")
    group.add_argument("--stats", action="store_true")
    parser.add_argument("--depth", type=int, default=1)
    parser.add_argument("--older-than-days", type=int, default=30)
    args = parser.parse_args(argv)

    if args.find:
        node = find(args.find)
        if node is None:
            print(json.dumps({"entity": args.find, "found": False}))
            return 1
        print(json.dumps(node, indent=2))
        return 0
    if args.neighbors:
        nbrs = neighbors(args.neighbors, args.depth)
        print(json.dumps({"entity": args.neighbors, "depth": args.depth, "neighbors": nbrs}, indent=2))
        return 0
    if args.by_type:
        out = by_type(args.by_type)
        print(json.dumps({"type": args.by_type, "nodes": out}, indent=2))
        return 0
    if args.stale:
        out = stale(args.older_than_days)
        print(json.dumps({"older_than_days": args.older_than_days, "stale": out}, indent=2))
        return 0
    if args.stats:
        print(json.dumps(stats(), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
