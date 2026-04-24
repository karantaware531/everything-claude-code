#!/usr/bin/env python3
"""
policy_guard.py — advisory policy checker.

Reads .claude/policies/security.yaml and answers "is this action allowed?"
Call before any file write, shell exec, or network request.

Usage:
    python policy_guard.py --action "<verb>:<target>"
        verbs: read, write, shell, network, agent.create, registry.amend
        target: path (for read/write), command (for shell), url (for network)

    python policy_guard.py --action "write:.env"                 # → deny
    python policy_guard.py --action "write:.claude/agents/x.md"  # → allow
    python policy_guard.py --action "shell:rm -rf /"             # → deny

Exit codes:
    0  — allowed
    1  — denied (reason on stderr; JSON verdict on stdout)
    2  — usage error
    3  — policy file missing or malformed (fail-closed → deny)

This is ADVISORY — nothing forces agents to call it. The real enforcement comes
from Claude Code's tool permission model. But agents that bypass this leave an
audit gap; the reflection agent will surface that pattern.

Stdlib only — includes a minimal YAML parser for the narrow subset of YAML we use.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # .claude/
POLICY = ROOT / "policies" / "security.yaml"


# ─── Minimal YAML subset parser ─────────────────────────────────────────────
# We only need: nested mappings, lists of strings, scalar strings/ints/bools.
# Written from scratch so we don't need PyYAML.

def _strip_inline_comment(line: str) -> str:
    """Drop '# comment' from end of a YAML line, but not inside quotes."""
    in_single = in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1].isspace():
                return line[:i].rstrip()
    return line


def _parse_yaml(text: str) -> Any:
    lines = [_strip_inline_comment(ln).rstrip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]
    idx = 0

    def current_indent() -> int:
        return len(lines[idx]) - len(lines[idx].lstrip())

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
        # Peek first non-empty line at >= base_indent
        if idx >= len(lines):
            return None
        first = lines[idx]
        first_indent = len(first) - len(first.lstrip())
        if first_indent < base_indent:
            return None
        stripped = first.lstrip()
        # list?
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
                if item == "" or item.endswith(":"):
                    # nested mapping under list item
                    key = item.rstrip(":").strip()
                    if key:
                        # "- name:" style with sub-mapping
                        sub = parse_block(base_indent + 2)
                        out_list.append({key: sub})
                    else:
                        sub = parse_block(base_indent + 2)
                        out_list.append(sub)
                else:
                    # inline "- value" or "- key: value"
                    if ":" in item and not (item.startswith('"') or item.startswith("'")):
                        k, _, v = item.partition(":")
                        entry = {k.strip(): parse_scalar(v)}
                        # Multi-line list-of-mappings: continuation lines indented
                        # MORE than the dash get folded into this same mapping.
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
        # mapping
        out_map: dict[str, Any] = {}
        while idx < len(lines):
            ln = lines[idx]
            ind = len(ln) - len(ln.lstrip())
            if ind < base_indent:
                break
            if ind > base_indent:
                break
            s = ln.lstrip()
            if ":" not in s:
                break
            key, _, rest = s.partition(":")
            key = key.strip()
            rest = rest.strip()
            idx += 1
            if rest == "":
                # nested block
                sub = parse_block(base_indent + 2)
                out_map[key] = sub
            elif rest.startswith("[") and rest.endswith("]"):
                # inline list: [a, b, c]
                inner = rest[1:-1]
                out_map[key] = [parse_scalar(x) for x in inner.split(",") if x.strip()]
            else:
                out_map[key] = parse_scalar(rest)
        return out_map

    result = parse_block(0)
    return result if result is not None else {}


def load_policy() -> dict:
    if not POLICY.exists():
        return {}
    text = POLICY.read_text(encoding="utf-8")
    return _parse_yaml(text) or {}


# ─── Verdicts ────────────────────────────────────────────────────────────────

def _match_any(path: str, patterns: list[str]) -> str | None:
    """Return the first matching pattern, or None."""
    if not patterns:
        return None
    norm = path.replace("\\", "/")
    for pat in patterns:
        if not isinstance(pat, str):
            continue
        # fnmatch handles *, ?, [seq], and we extend for ** by translating to .*
        regex = fnmatch.translate(pat).replace(r"(?s:", "(?s:").replace(r"\*\*", ".*")
        # Simpler: use fnmatch directly with both the full path and the basename;
        # also handle ** by splitting on '/' and checking each segment.
        if fnmatch.fnmatch(norm, pat):
            return pat
        # Expand ** manually for nested glob match
        if "**" in pat:
            esc = re.escape(pat).replace(r"\*\*", ".*").replace(r"\*", "[^/]*").replace(r"\?", ".")
            if re.fullmatch(esc, norm):
                return pat
    return None


def check_file_action(verb: str, target: str, policy: dict) -> tuple[bool, str]:
    fa = policy.get("file_access", {}) or {}
    section = fa.get(verb, {}) or {}
    denied = section.get("denied") or []
    allowed = section.get("allowed") or []

    hit = _match_any(target, denied)
    if hit:
        return False, f"denied by file_access.{verb}.denied pattern '{hit}'"

    if verb == "write" and allowed:
        hit = _match_any(target, allowed)
        if hit:
            return True, f"allowed by file_access.write.allowed pattern '{hit}'"
        # Writes outside the allowed list default to deny.
        return False, "no allow rule matched; writes default to deny"

    # For read, absence of explicit deny is allow.
    return True, "no deny rule matched"


def check_shell(command: str, policy: dict) -> tuple[bool, str]:
    tools = policy.get("tools", {}) or {}
    shell = tools.get("shell", {}) or {}
    denied = shell.get("denied_patterns") or []
    for pat in denied:
        if not isinstance(pat, str):
            continue
        if pat in command:
            return False, f"denied by tools.shell.denied_patterns substring '{pat}'"
    return True, "no shell deny pattern matched"


def check_network(url_or_tool: str, policy: dict) -> tuple[bool, str]:
    tools = policy.get("tools", {}) or {}
    net = tools.get("network", {}) or {}
    allowed_tools = net.get("allowed_tools") or []
    # target can be either a tool name or a URL; accept either matching pattern
    for allowed in allowed_tools:
        if isinstance(allowed, str) and allowed in url_or_tool:
            return True, f"allowed — {allowed} is in tools.network.allowed_tools"
    return False, f"network action not permitted for '{url_or_tool}'"


def check_governance(verb: str, policy: dict) -> tuple[bool, str]:
    gov = policy.get("governance", {}) or {}
    approval = gov.get("requires_user_approval") or []
    # `verb` here is a governance verb like "constitution.amend"
    if verb in approval:
        return False, f"action '{verb}' requires explicit user approval"
    return True, "no governance block"


def evaluate(action: str, policy: dict) -> dict:
    if ":" not in action:
        return {"allowed": False, "reason": "action must be '<verb>:<target>'", "action": action}
    verb, _, target = action.partition(":")
    verb = verb.strip().lower()
    target = target.strip()

    if verb in ("read", "write"):
        ok, reason = check_file_action(verb, target, policy)
    elif verb == "shell":
        ok, reason = check_shell(target, policy)
    elif verb == "network":
        ok, reason = check_network(target, policy)
    elif verb in ("agent.create", "registry.amend", "constitution.amend", "policy.edit"):
        ok, reason = check_governance(verb, policy)
    else:
        ok, reason = False, f"unknown verb '{verb}'"

    return {
        "action": action,
        "verb": verb,
        "target": target,
        "allowed": ok,
        "reason": reason,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--action", required=True, help="'<verb>:<target>' — verb in {read, write, shell, network, agent.create, registry.amend}")
    parser.add_argument("--policy", type=Path, default=POLICY, help="path to security.yaml")
    args = parser.parse_args(argv)

    if not args.policy.exists():
        print(json.dumps({"allowed": False, "reason": f"policy file missing: {args.policy}"}, indent=2), file=sys.stdout)
        return 3

    try:
        policy = load_policy() if args.policy == POLICY else _parse_yaml(args.policy.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"allowed": False, "reason": f"policy parse error: {e}"}, indent=2), file=sys.stdout)
        return 3

    verdict = evaluate(args.action, policy or {})
    print(json.dumps(verdict, indent=2))
    return 0 if verdict["allowed"] else 1


if __name__ == "__main__":
    sys.exit(main())
