#!/usr/bin/env python3
"""post_compact_reinject.py — PostCompact hook: re-inject critical context after compaction.

After Claude compacts the conversation, the summary retains high-level info but may
lose specific state. This hook surfaces key facts back into context via stdout (which
is injected into Claude on the next turn).

What we re-inject:
  - Current session goal (memory/goals_state.json)
  - Last 3 agent invocations (memory/agent_history.json)
  - Active budget state (memory/budgets.json)
  - Any notes/ file touched in the last 1 hour

Exit 0 always; never blocks.

Disable: AGENTIC_OS_HOOKS_DISABLED=1
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"

HOOKS_DIR = Path(__file__).resolve().parent
ROOT = HOOKS_DIR.parent  # .claude/
MEMORY = ROOT / "memory"
NOTES = ROOT / "notes"


def _safe_json(p: Path) -> dict | list | None:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return None


def main() -> int:
    if DISABLED:
        return 0

    lines: list[str] = ["[PostCompact context re-injection]"]

    # 1. Current goal
    goals = _safe_json(MEMORY / "goals_state.json") or {}
    if goals.get("current_goal"):
        lines.append(f"- Current goal: {goals['current_goal']}")
        subs = goals.get("active_subgoals", [])
        if subs:
            lines.append(f"- Active subgoals: {len(subs)}")

    # 2. Recent agents (last 3)
    history = _safe_json(MEMORY / "agent_history.json")
    if isinstance(history, dict):
        entries = history.get("entries", [])
    elif isinstance(history, list):
        entries = history
    else:
        entries = []
    if entries:
        last3 = entries[-3:]
        agent_seq = " -> ".join(e.get("agent", "?") for e in last3 if isinstance(e, dict))
        lines.append(f"- Last agents: {agent_seq}")

    # 3. Active budgets
    budgets = _safe_json(MEMORY / "budgets.json") or {}
    active = budgets.get("active", {}) if isinstance(budgets, dict) else {}
    if active:
        lines.append(f"- Active budgets: {len(active)} task(s)")

    # 4. Recently-written notes (last hour)
    cutoff = time.time() - 3600
    recent_notes: list[str] = []
    if NOTES.exists():
        for p in NOTES.rglob("*.md"):
            try:
                if p.stat().st_mtime > cutoff:
                    recent_notes.append(str(p.relative_to(ROOT.parent)))
            except OSError:
                pass
    if recent_notes:
        lines.append(f"- Recently updated notes ({len(recent_notes)}): {', '.join(recent_notes[:5])}")

    lines.append(f"- Compaction time: {datetime.now(timezone.utc).isoformat()}")
    lines.append("Consult graphify_agent or run /graphify-query for deep context.")

    print("\n".join(lines))  # stdout -> injected into Claude context
    return 0


if __name__ == "__main__":
    sys.exit(main())
