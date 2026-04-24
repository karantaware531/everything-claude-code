#!/usr/bin/env python3
"""
gateguard.py — PreToolUse hook: GateGuard pre-action fact-forcing gate.

Adapted from everything-claude-code's GateGuard pattern.
Measured impact: +2.25 quality points average across edit tasks.

Key insight: "Investigation itself creates context that self-evaluation never did."
Forcing the model to declare file dependencies, affected functions, and schemas
before any edit eliminates a class of quality failures caused by acting on
incomplete knowledge.

How it works:
- Intercepts Edit/MultiEdit/Write/NotebookEdit tool calls.
- Checks the tool input for a gateguard declaration block.
- If declaration is missing AND the file is non-trivial (>20 lines), emits
  a soft warning to stdout (does NOT block — advisory mode).
- Hard block (exit 2) only for files matching HARD_BLOCK_PATTERNS.

Exit codes:
  0 = proceed (gate satisfied or file is trivial)
  2 = block (hard-block file pattern detected without gate declaration)

Disable: set AGENTIC_OS_HOOKS_DISABLED=1
Profile: set AGENTIC_OS_GATEGUARD_PROFILE=off|advisory|strict
  off       = no-op
  advisory  = warn to stdout, never block (default)
  strict    = block on missing gate for any file >10 lines
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"
PROFILE = os.environ.get("AGENTIC_OS_GATEGUARD_PROFILE", "advisory").lower()

# File patterns that require a gate declaration or get hard-blocked.
# These are high-impact files where acting without investigation is dangerous.
HARD_BLOCK_PATTERNS = [
    "security.yaml",
    "policies/",
    "CLAUDE.md",
    "registry.json",
    "agent_history.json",
    "trust_matrix.json",
]

# Marker that satisfies the gate — must appear in the tool call's description/comment
# OR the hook can be satisfied by a preceding Read call in the same session.
GATE_MARKERS = [
    "GATE:",
    "gate:",
    "# dependencies:",
    "# affected:",
    "GateGuard:",
    "gateguard:",
]

TRIVIAL_LINE_THRESHOLD = 20  # files shorter than this are not gated


def _load_event() -> dict:
    """Read the Claude Code hook event JSON from stdin."""
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def _file_path(event: dict) -> str | None:
    inp = event.get("tool_input") or {}
    return inp.get("file_path") or inp.get("path") or inp.get("notebook_path")


def _is_hard_block(path: str) -> bool:
    for pattern in HARD_BLOCK_PATTERNS:
        if pattern in path:
            return True
    return False


def _gate_declared(event: dict) -> bool:
    """Return True if the tool call carries a gate declaration."""
    # Check description field (some tools support it)
    inp = event.get("tool_input") or {}
    for field in ("description", "comment", "new_string", "content"):
        val = str(inp.get(field, ""))
        if any(marker in val for marker in GATE_MARKERS):
            return True
    return False


def _file_line_count(path: str) -> int:
    try:
        p = Path(path)
        if p.exists():
            return len(p.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:  # noqa: BLE001
        pass
    return 0


def main() -> int:
    if DISABLED or PROFILE == "off":
        return 0

    event = _load_event()
    if not event:
        return 0

    tool_name = event.get("tool_name", "")
    if tool_name not in ("Edit", "MultiEdit", "Write", "NotebookEdit"):
        return 0

    path = _file_path(event)
    if not path:
        return 0

    # Hard block: high-impact files without a gate declaration
    if _is_hard_block(path) and not _gate_declared(event):
        print(
            f"[GateGuard] BLOCKED: '{path}' is a protected file.\n"
            "Before editing, declare:\n"
            "  GATE: dependencies=<list>, affected_functions=<list>, rollback=<plan>\n"
            "Or disable hard-block with AGENTIC_OS_GATEGUARD_PROFILE=advisory",
            file=sys.stderr,
        )
        return 2

    # Advisory: non-trivial files without gate declaration
    if PROFILE in ("advisory", "strict"):
        line_threshold = 10 if PROFILE == "strict" else TRIVIAL_LINE_THRESHOLD
        if not _gate_declared(event) and _file_line_count(path) > line_threshold:
            print(
                f"[GateGuard] Advisory: editing '{path}' ({_file_line_count(path)} lines) "
                "without a gate declaration.\n"
                "For +2.25 quality improvement, declare before editing:\n"
                "  GATE: dependencies=<affected files>, "
                "affected_functions=<names>, schema_changes=<yes|no>\n"
                "Proceeding anyway (advisory mode)."
            )
            # In advisory mode, do NOT block — just warn
            if PROFILE == "strict":
                return 2
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
