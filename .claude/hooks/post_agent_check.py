#!/usr/bin/env python3
"""
post_agent_check.py — PostToolUse(Agent) hook.

Runs after every Agent tool call completes. Responsibilities:
  1. Record the agent invocation in agent_history.json (duration, outcome).
  2. Append a trace envelope to observability/traces.json.
  3. If the agent output carries a task_file path, update the task's status
     to 'complete' or 'failed' based on the output.
  4. Emit a Ship Council reminder if the agent produced code changes.

Never blocks (exit 0 always). Informational + bookkeeping only.

Disable with AGENTIC_OS_HOOKS_DISABLED=1
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"

ROOT = Path(__file__).resolve().parents[1]          # .claude/
PROJECT_ROOT = ROOT.parent
AGENT_HISTORY = ROOT / "memory" / "agent_history.json"
TRACES_PATH = ROOT / "observability" / "traces.json"

# Agent output fields that indicate code was produced (triggers Ship Council reminder)
CODE_CHANGE_SIGNALS = ("changed_files", "diff", "patch", "files_modified")


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def _load_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _parse_agent_output(output) -> dict:
    """Try to parse agent output as JSON; fall back to raw string."""
    if isinstance(output, dict):
        return output
    if isinstance(output, str):
        try:
            return json.loads(output)
        except (json.JSONDecodeError, ValueError):
            return {"raw": output[:500]}
    return {}


def _update_task_file(task_file: str, outcome: str) -> None:
    """Update the status field in a task markdown frontmatter."""
    import re
    p = Path(task_file)
    if not p.is_absolute():
        p = PROJECT_ROOT / task_file
    if not p.exists():
        return
    try:
        content = p.read_text(encoding="utf-8")
        new_status = "complete" if outcome == "success" else "failed"
        updated = re.sub(
            r"^(status\s*:\s*).*$",
            f"\\g<1>{new_status}",
            content,
            flags=re.MULTILINE,
        )
        if updated != content:
            p.write_text(updated, encoding="utf-8")
    except OSError:
        pass


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
    tool_output = event.get("tool_response") or event.get("output") or {}
    agent_name = (
        tool_input.get("subagent_type")
        or tool_input.get("agent")
        or tool_input.get("name")
        or "unknown"
    )
    task_id = event.get("task_id") or event.get("session_id") or "unknown"
    task_file = tool_input.get("task_file") or tool_input.get("task_markdown")
    duration_ms = event.get("duration_ms")
    now = datetime.now(timezone.utc)
    ts = now.isoformat()

    # Parse structured output
    parsed_output = _parse_agent_output(tool_output)
    outcome = "success"
    if isinstance(tool_output, str) and any(
        kw in tool_output.lower() for kw in ("error", "failed", "exception", "blocked")
    ):
        outcome = "failure"
    if parsed_output.get("outcome") in ("failure", "failed", "error"):
        outcome = "failure"

    # 1. Record in agent_history.json
    history = _load_json(AGENT_HISTORY, {"entries": []})
    entries = history.get("entries") or []
    entries.append({
        "agent": agent_name,
        "task_id": task_id,
        "timestamp": ts,
        "duration_ms": duration_ms,
        "outcome": outcome,
        "success": outcome == "success",
        "is_new_agent": False,  # factory sets this to True when it creates a new agent
        "task_file": task_file,
        "output_summary": parsed_output.get("summary") or parsed_output.get("raw", "")[:200],
    })
    # Keep last 500 entries
    history["entries"] = entries[-500:]
    _save_json(AGENT_HISTORY, history)

    # 2. Append trace envelope
    traces = _load_json(TRACES_PATH, [])
    if not isinstance(traces, list):
        traces = []
    traces.append({
        "from": "hook:post_agent_check",
        "to": agent_name,
        "task_id": task_id,
        "trace_id": f"agent-post-{now.strftime('%Y%m%d%H%M%S%f')}",
        "kind": "agent_completion",
        "timestamp": ts,
        "payload": {
            "outcome": outcome,
            "duration_ms": duration_ms,
            "task_file": task_file,
            "changed_files": parsed_output.get("changed_files"),
            "output_summary": parsed_output.get("summary", "")[:300],
        },
        "protocol_version": "1.0",
    })
    _save_json(TRACES_PATH, traces)

    # 3. Update task file status if present
    if task_file:
        _update_task_file(task_file, outcome)

    # 4. Ship Council reminder if code was produced
    has_code_changes = any(
        parsed_output.get(sig) for sig in CODE_CHANGE_SIGNALS
    )
    if has_code_changes:
        print(
            f"[post_agent_check] Agent '{agent_name}' produced code changes. "
            "Route output through Ship Council (critic → evaluator → security) "
            "before advancing the DAG."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
