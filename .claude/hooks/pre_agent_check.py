#!/usr/bin/env python3
"""
pre_agent_check.py — PreToolUse(Agent) hook.

Validates every Agent tool call before dispatch:
  1. Agent name exists in registry.json (or is a voltagent/plugin specialist).
  2. New-agent budget not exceeded (max 2 novel agents per task).
  3. DAG depth cap not exceeded (max 5).
  4. If tool_input carries a 'task_file' path, validates the task markdown
     exists and has required frontmatter (task_id, agent, status).

Exit 0  — allow (or fail-open on any unexpected error)
Exit 2  — BLOCK; stderr surfaced to Claude as rejection reason

Disable with AGENTIC_OS_HOOKS_DISABLED=1
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"

ROOT = Path(__file__).resolve().parents[1]          # .claude/
PROJECT_ROOT = ROOT.parent
REGISTRY_PATH = ROOT / "registry.json"
TRACES_PATH = ROOT / "observability" / "traces.json"
AGENT_HISTORY = ROOT / "memory" / "agent_history.json"

# Prefixes that are always considered valid (plugin/voltagent specialists)
VALID_PREFIXES = (
    "voltagent-", "gitnexus-", "design:", "engineering:", "data:",
    "bio-research:", "product-management:", "product-tracking-skills:",
    "anthropic-skills:", "figma:", "superpowers:", "feature-dev:",
    "cowork-plugin-management:", "productivity:", "claude-code-guide",
    "general-purpose", "Explore", "Plan", "code_agent", "research_agent",
    "tool_executor", "graphify_agent",
)

MAX_NEW_AGENTS_PER_TASK = 2
MAX_DAG_DEPTH = 5

# Required frontmatter keys in task markdown files
TASK_REQUIRED_KEYS = {"task_id", "agent", "status"}


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _load_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _registered_agent_names() -> set[str]:
    data = _load_json(REGISTRY_PATH, {"agents": []})
    agents = data.get("agents") or []
    return {a.get("name", "") for a in agents if a.get("name")}


def _is_valid_agent(name: str, registered: set[str]) -> bool:
    if name in registered:
        return True
    return any(name.startswith(p) for p in VALID_PREFIXES)


def _current_task_id(event: dict) -> str:
    return event.get("task_id") or event.get("session_id") or "unknown"


def _count_new_agents_this_task(task_id: str) -> int:
    """Count how many novel (factory-created) agents were dispatched in this task."""
    entries = _load_json(AGENT_HISTORY, {"entries": []}).get("entries") or []
    count = 0
    for e in reversed(entries[-100:]):
        if e.get("task_id") == task_id and e.get("is_new_agent"):
            count += 1
    return count


def _current_dag_depth(task_id: str) -> int:
    """Estimate DAG depth from traces for this task."""
    traces = _load_json(TRACES_PATH, [])
    if not isinstance(traces, list):
        return 0
    depth = sum(
        1 for t in traces
        if isinstance(t, dict) and t.get("task_id") == task_id
        and t.get("kind") in ("agent_dispatch", "subagent_lifecycle")
    )
    return depth


def _validate_task_file(task_file: str) -> str | None:
    """Return an error string if the task file is missing or malformed, else None."""
    p = Path(task_file)
    if not p.is_absolute():
        p = PROJECT_ROOT / task_file
    if not p.exists():
        return f"task_file '{task_file}' not found"
    content = p.read_text(encoding="utf-8", errors="ignore")
    # Parse YAML frontmatter between --- delimiters
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        return f"task_file '{task_file}' missing YAML frontmatter (--- ... ---)"
    fm_text = fm_match.group(1)
    found_keys = set(re.findall(r"^(\w+)\s*:", fm_text, re.MULTILINE))
    missing = TASK_REQUIRED_KEYS - found_keys
    if missing:
        return f"task_file '{task_file}' missing required frontmatter keys: {missing}"
    return None


def main() -> int:
    if DISABLED:
        return 0

    event = _load_event()
    if not event:
        return 0

    tool_name = event.get("tool_name", "")
    if tool_name != "Agent":
        return 0

    tool_input = event.get("tool_input") or {}
    agent_name = (
        tool_input.get("subagent_type")
        or tool_input.get("agent")
        or tool_input.get("name")
        or ""
    )
    task_file = tool_input.get("task_file") or tool_input.get("task_markdown")
    task_id = _current_task_id(event)

    # 1. Registry / known-prefix check
    registered = _registered_agent_names()
    if agent_name and not _is_valid_agent(agent_name, registered):
        print(
            f"[pre_agent_check] BLOCKED: agent '{agent_name}' not found in registry "
            "and does not match any known specialist prefix.\n"
            "Register via registry_manager before dispatching.",
            file=sys.stderr,
        )
        return 2

    # 2. New-agent budget
    new_count = _count_new_agents_this_task(task_id)
    if new_count >= MAX_NEW_AGENTS_PER_TASK:
        print(
            f"[pre_agent_check] BLOCKED: new-agent budget exhausted "
            f"({new_count}/{MAX_NEW_AGENTS_PER_TASK} for task '{task_id}').\n"
            "Reuse an existing agent or request a tier-4 budget override.",
            file=sys.stderr,
        )
        return 2

    # 3. DAG depth cap
    depth = _current_dag_depth(task_id)
    if depth >= MAX_DAG_DEPTH:
        print(
            f"[pre_agent_check] BLOCKED: DAG depth cap reached "
            f"(depth={depth}, max={MAX_DAG_DEPTH}) for task '{task_id}'.\n"
            "Halt and escalate to user (tier ≥ 3).",
            file=sys.stderr,
        )
        return 2

    # 4. Task file validation (if provided)
    if task_file:
        err = _validate_task_file(task_file)
        if err:
            print(
                f"[pre_agent_check] BLOCKED: {err}\n"
                "Fix the task markdown file before dispatching the agent.",
                file=sys.stderr,
            )
            return 2

    # All checks passed — emit advisory to stdout (injected into Claude context)
    print(
        f"[pre_agent_check] OK: agent='{agent_name}' task_id='{task_id}' "
        f"depth={depth} new_agents={new_count}"
        + (f" task_file={task_file}" if task_file else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
