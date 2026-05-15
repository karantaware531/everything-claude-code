#!/usr/bin/env python3
"""
pre_validate_tool_input.py — PreToolUse(*) general validation hook.

Fires on EVERY tool call. Performs lightweight structural checks:
  1. Prompt/description injection pattern scan (override attempts, role-hijack).
  2. File path boundary check (Write/Edit targets must be within project root
     or allowed absolute paths).
  3. JSON schema spot-check on tool_input for known tools.
  4. Detects suspiciously large payloads that could indicate exfiltration.

This hook is deliberately fast (<20ms) — it delegates deep analysis to the
tool-specific hooks (enforce_policy_on_bash, enforce_policy_on_write, etc.).

Exit 0  — allow
Exit 2  — BLOCK; stderr surfaced to Claude

Disable with AGENTIC_OS_HOOKS_DISABLED=1
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DISABLED = os.environ.get("AGENTIC_OS_HOOKS_DISABLED", "").strip() == "1"

ROOT = Path(__file__).resolve().parents[1]          # .claude/
PROJECT_ROOT = ROOT.parent

# Max bytes in any single string field before we flag it as suspicious
MAX_FIELD_BYTES = 200_000

# Patterns that suggest prompt injection / override attempts
# Checked in description, prompt, comment, and content fields
INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "new instructions:",
    "system prompt:",
    "you are now",
    "pretend you are",
    "act as if you",
    "jailbreak",
    "dan mode",
    "developer mode",
    "override your",
    "bypass your",
    "forget your instructions",
    "AGENTIC_OS_HOOKS_DISABLED",   # hook kill-switch injection
    "AGENTIC_OS_NIGHTLY_DISABLED",
    "constitution_amendment",      # amendment bypass attempt
]

# Tools that write files — we check their paths stay within the project
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

# Paths that are always off-limits for writes (belt-and-suspenders; gateguard also checks)
PROTECTED_ROOTS = [
    ".git/",
    ".vscode/",
    ".idea/",
    ".gitconfig",
    ".bashrc",
    ".zshrc",
]

# Fields to scan for injection patterns
SCAN_FIELDS = ("description", "prompt", "comment", "new_string", "content", "command")


def _load_event() -> dict:
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _check_injection(tool_input: dict) -> str | None:
    """Return a reason string if injection pattern detected, else None."""
    for field in SCAN_FIELDS:
        val = str(tool_input.get(field, "")).lower()
        for pattern in INJECTION_PATTERNS:
            if pattern.lower() in val:
                return f"injection pattern '{pattern}' in field '{field}'"
    return None


def _check_path_boundary(tool_name: str, tool_input: dict) -> str | None:
    """Return a reason string if a write target is outside allowed roots, else None."""
    if tool_name not in WRITE_TOOLS:
        return None
    path_str = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("notebook_path")
        or ""
    )
    if not path_str:
        return None
    p = Path(path_str)
    # Absolute paths outside project root are suspicious
    if p.is_absolute():
        try:
            p.relative_to(PROJECT_ROOT)
        except ValueError:
            # Check if it's under any common allowed absolute paths
            allowed_abs = [
                Path.home() / ".claude",
            ]
            if not any(str(p).startswith(str(a)) for a in allowed_abs):
                return f"write target '{path_str}' is outside project root and not in allowed paths"
    # Protected root patterns
    normalized = path_str.replace("\\", "/")
    for prot in PROTECTED_ROOTS:
        if prot in normalized:
            return f"write target '{path_str}' matches protected root pattern '{prot}'"
    return None


def _check_payload_size(tool_input: dict) -> str | None:
    """Return a reason string if any field is suspiciously large."""
    for key, val in tool_input.items():
        if isinstance(val, str) and len(val.encode("utf-8")) > MAX_FIELD_BYTES:
            return (
                f"field '{key}' is {len(val)} chars "
                f"(max {MAX_FIELD_BYTES // 1000}KB). Possible exfiltration payload."
            )
    return None


def main() -> int:
    if DISABLED:
        return 0

    event = _load_event()
    if not event:
        return 0

    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input") or {}

    # 1. Injection pattern scan
    reason = _check_injection(tool_input)
    if reason:
        print(
            f"[pre_validate] BLOCKED: {reason}\n"
            "This looks like a prompt injection attempt. "
            "If this is a legitimate edit, remove the flagged text and retry.",
            file=sys.stderr,
        )
        return 2

    # 2. Path boundary check
    reason = _check_path_boundary(tool_name, tool_input)
    if reason:
        print(
            f"[pre_validate] BLOCKED: {reason}\n"
            "Writes must target files within the project root or ~/.claude/.",
            file=sys.stderr,
        )
        return 2

    # 3. Payload size check (advisory — block only on extreme overrun)
    reason = _check_payload_size(tool_input)
    if reason:
        print(
            f"[pre_validate] WARNING: {reason}\n"
            "Proceeding, but this is unusual. Verify intent.",
        )
        # Advisory only — do not block

    return 0


if __name__ == "__main__":
    sys.exit(main())
