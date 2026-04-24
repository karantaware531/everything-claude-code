#!/usr/bin/env python3
"""
harness_audit.py — 7-category Claude Code harness quality scorer.

Adapted from everything-claude-code's harness-audit.js, ported to Python
to stay within the Agentic OS stdlib-only constraint.

Categories (each scored 0-10, then normalized):
  1. Tool Coverage      — are the right agents registered?
  2. Context Efficiency — is CLAUDE.md lean? Are MCPs configured?
  3. Quality Gates      — hooks enforcing quality (GateGuard, policy, invariant)?
  4. Memory Persistence — session save, precompact hook, goals state?
  5. Eval Coverage      — does the test_runner cover the system?
  6. Security Guardrails — allowlist/denylist, hook enforcement, policies?
  7. Cost Efficiency    — token budget, domain policies, utility function?

Exit 0 with JSON output to stdout.
Human-readable summary to stderr.

Usage:
  python .claude/tools/harness_audit.py
  python .claude/tools/harness_audit.py --json       (JSON only, no summary)
  python .claude/tools/harness_audit.py --category 3 (single category)
  python .claude/tools/harness_audit.py --threshold 7 (exit 1 if overall < threshold)
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REPO_ROOT = ROOT.parent                      # project root


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exists(p: Path) -> bool:
    return p.exists()


def _file_count(directory: Path, pattern: str = "*.md") -> int:
    if not directory.exists():
        return 0
    return len(list(directory.glob(pattern)))


def _json_valid(p: Path) -> bool:
    try:
        json.loads(p.read_text(encoding="utf-8"))
        return True
    except Exception:  # noqa: BLE001
        return False


def _py_parses(p: Path) -> bool:
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        return True
    except Exception:  # noqa: BLE001
        return False


def _line_count(p: Path) -> int:
    try:
        return len(p.read_text(encoding="utf-8").splitlines())
    except Exception:  # noqa: BLE001
        return 0


def _registry_agent_count() -> int:
    reg = ROOT / "registry.json"  # v5.2: moved from wiki/
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
        return len(data.get("agents", []))
    except Exception:  # noqa: BLE001
        return 0


# ---------------------------------------------------------------------------
# Category 1: Tool Coverage
# ---------------------------------------------------------------------------
def audit_tool_coverage() -> tuple[float, list[str], list[str]]:
    """Are the right agents registered and do they have agent files?"""
    findings: list[str] = []
    issues: list[str] = []

    agent_count = _registry_agent_count()
    # v5.5: 21 agents baseline (orchestrator retired; main session = Lead Agent per Agent Teams protocol)
    if agent_count >= 21:
        findings.append(f"Registry: {agent_count} agents (target >=21, v5.5 Lead Agent baseline)")
    else:
        issues.append(f"Registry: only {agent_count} agents (target >=21)")

    layers = {
        "cognitive": ROOT / "agents" / "cognitive",
        "execution": ROOT / "agents" / "execution",
        "governance": ROOT / "agents" / "governance",
        "meta": ROOT / "agents" / "meta",
    }
    total_md = 0
    for layer, path in layers.items():
        count = _file_count(path)
        total_md += count
        if count > 0:
            findings.append(f"Layer {layer}: {count} agents")
        else:
            issues.append(f"Layer {layer}: missing (0 agents)")

    tool_registry = ROOT / "tools" / "tool_registry.json"
    if _exists(tool_registry) and _json_valid(tool_registry):
        data = json.loads(tool_registry.read_text(encoding="utf-8"))
        tool_count = len(data.get("tools", []))
        if tool_count >= 8:
            findings.append(f"Tool registry: {tool_count} tools")
        else:
            issues.append(f"Tool registry: only {tool_count} tools (target >=8)")
    else:
        issues.append("tool_registry.json missing or invalid")

    score = max(0.0, 10.0 - len(issues) * 2.0)
    return score, findings, issues


# ---------------------------------------------------------------------------
# Category 2: Context Efficiency
# ---------------------------------------------------------------------------
def audit_context_efficiency() -> tuple[float, list[str], list[str]]:
    """Is the context lean? MCPs configured? CLAUDE.md not bloated?"""
    findings: list[str] = []
    issues: list[str] = []

    # Root CLAUDE.md should exist and be lean (< 40 lines)
    root_claude = REPO_ROOT / "CLAUDE.md"
    if _exists(root_claude):
        lines = _line_count(root_claude)
        if lines <= 40:
            findings.append(f"Root CLAUDE.md: {lines} lines (lean)")
        else:
            issues.append(f"Root CLAUDE.md: {lines} lines (target <40; bloats every context)")
    else:
        issues.append("Root CLAUDE.md missing (Claude Code won't load constitution)")

    # .mcp.json configured
    mcp = REPO_ROOT / ".mcp.json"
    if _exists(mcp) and _json_valid(mcp):
        data = json.loads(mcp.read_text(encoding="utf-8"))
        server_count = len(data.get("mcpServers", {}))
        if server_count >= 3:
            findings.append(f"MCP servers configured: {server_count}")
        else:
            issues.append(f"MCP: only {server_count} servers (target >=3 for live data)")
    else:
        issues.append(".mcp.json missing — no live data sources configured")

    # Commands directory (slash commands)
    commands = _file_count(ROOT / "commands")
    if commands >= 6:
        findings.append(f"Slash commands: {commands}")
    else:
        issues.append(f"Slash commands: only {commands} (target >=6)")

    # identity.json
    if _exists(ROOT / "identity.json"):
        findings.append("identity.json: user persona configured")
    else:
        issues.append("identity.json missing — Claude doesn't know verbosity/style preferences")

    score = max(0.0, 10.0 - len(issues) * 2.5)
    return score, findings, issues


# ---------------------------------------------------------------------------
# Category 3: Quality Gates
# ---------------------------------------------------------------------------
def audit_quality_gates() -> tuple[float, list[str], list[str]]:
    """Are quality-enforcing hooks in place?"""
    findings: list[str] = []
    issues: list[str] = []

    hooks_dir = ROOT / "hooks"
    required_hooks = {
        "enforce_policy_on_bash.py": "PreToolUse Bash policy",
        "enforce_policy_on_write.py": "PreToolUse Write policy",
        "karpathy_invariant_check.py": "PostToolUse Karpathy check",
        "session_health_probe.py": "SessionStart health probe",
        "suggest_epoch_learner.py": "Stop epoch reminder",
        "gateguard.py": "PreToolUse GateGuard (+2.25 quality)",
        "precompact_state_saver.py": "PreCompact session persistence",
    }
    for script, desc in required_hooks.items():
        p = hooks_dir / script
        if _exists(p) and _py_parses(p):
            findings.append(f"Hook: {script} ({desc})")
        else:
            issues.append(f"Missing hook: {script} ({desc})")

    # settings.json registers hooks
    settings = ROOT / "settings.json"
    if _exists(settings) and _json_valid(settings):
        data = json.loads(settings.read_text(encoding="utf-8"))
        events = set(data.get("hooks", {}).keys())
        target_events = {"SessionStart", "PreToolUse", "PostToolUse", "Stop"}
        if target_events <= events:
            findings.append(f"settings.json: all {len(events)} lifecycle events registered")
        else:
            missing = target_events - events
            issues.append(f"settings.json: missing events {missing}")
    else:
        issues.append("settings.json missing — hooks not registered")

    score = max(0.0, 10.0 - len(issues) * 1.25)
    return score, findings, issues


# ---------------------------------------------------------------------------
# Category 4: Memory Persistence
# ---------------------------------------------------------------------------
def audit_memory_persistence() -> tuple[float, list[str], list[str]]:
    """Session save, goals state, system profile, Karpathy invariant."""
    findings: list[str] = []
    issues: list[str] = []

    memory = ROOT / "memory"

    required_json = {
        "logs.json": "task-level outcomes",
        "agent_history.json": "per-invocation records",
        "goals_state.json": "session goal state",
        "system_profile.json": "self-model profile",
        "budgets.json": "token/time budgets",
    }
    for fname, desc in required_json.items():
        p = memory / fname
        if _exists(p) and _json_valid(p):
            findings.append(f"Memory: {fname} ({desc})")
        else:
            issues.append(f"Missing/invalid: memory/{fname} ({desc})")

    # Karpathy invariant: no .md in memory/
    md_files = list(memory.rglob("*.md")) if memory.exists() else []
    if not md_files:
        findings.append("Karpathy invariant: no .md in memory/ (PASS)")
    else:
        issues.append(f"Karpathy invariant VIOLATED: {len(md_files)} .md files in memory/")

    # precompact hook exists (saves before compaction)
    if _exists(ROOT / "hooks" / "precompact_state_saver.py"):
        findings.append("PreCompact hook: session state preserved before compaction")
    else:
        issues.append("PreCompact hook missing — compaction loses session context")

    # /save-session command
    if _exists(ROOT / "commands" / "save-session.md"):
        findings.append("/save-session command available")
    else:
        issues.append("/save-session command missing")

    score = max(0.0, 10.0 - len(issues) * 1.5)
    return score, findings, issues


# ---------------------------------------------------------------------------
# Category 5: Eval Coverage
# ---------------------------------------------------------------------------
def audit_eval_coverage() -> tuple[float, list[str], list[str]]:
    """Does the test_runner cover the system comprehensively?"""
    findings: list[str] = []
    issues: list[str] = []

    test_runner = ROOT / "tools" / "test_runner.py"
    if not _exists(test_runner):
        return 0.0, [], ["test_runner.py missing"]

    content = test_runner.read_text(encoding="utf-8")

    # Count check functions
    import re
    check_fns = re.findall(r"def check_\d+_", content)
    check_count = len(check_fns)
    if check_count >= 28:
        findings.append(f"test_runner: {check_count} checks")
    elif check_count >= 22:
        issues.append(f"test_runner: {check_count} checks (target >=28)")
    else:
        issues.append(f"test_runner: only {check_count} checks (critically low)")

    # Check that v5 features are covered
    v5_markers = ["utility", "strategy_generator", "world_model", "consolidator", "keyword-tfidf"]
    for marker in v5_markers:
        if marker in content:
            findings.append(f"v5 coverage: {marker}")
        else:
            issues.append(f"v5 not covered: {marker}")

    # Hooks coverage
    if "hooks" in content.lower() and "settings.json" in content:
        findings.append("Hook configuration tested")
    else:
        issues.append("Hook configuration not tested")

    score = max(0.0, 10.0 - len(issues) * 1.5)
    return score, findings, issues


# ---------------------------------------------------------------------------
# Category 6: Security Guardrails
# ---------------------------------------------------------------------------
def audit_security_guardrails() -> tuple[float, list[str], list[str]]:
    """allowlist/denylist, hook enforcement, constitution, values."""
    findings: list[str] = []
    issues: list[str] = []

    security_yaml = ROOT / "policies" / "security.yaml"
    if _exists(security_yaml):
        content = security_yaml.read_text(encoding="utf-8")
        if "denied:" in content and "allowed:" in content:
            findings.append("security.yaml: allowlist + denylist configured")
        else:
            issues.append("security.yaml: incomplete (missing denied: or allowed:)")
        if ".env" in content:
            findings.append("security.yaml: .env in denylist")
        else:
            issues.append("security.yaml: .env not protected")
    else:
        issues.append("security.yaml missing")

    values_yaml = ROOT / "policies" / "values.yaml"
    if _exists(values_yaml):
        findings.append("values.yaml: declared values for critic alignment check")
    else:
        issues.append("values.yaml missing — no value alignment checking")

    governance_yaml = ROOT / "policies" / "governance.yaml"
    if _exists(governance_yaml):
        findings.append("governance.yaml: HITL tier rules defined")
    else:
        issues.append("governance.yaml missing — no tier escalation rules")

    domain_policies = ROOT / "policies" / "domain_policies.yaml"
    if _exists(domain_policies):
        findings.append("domain_policies.yaml: per-domain tier adjustments")
    else:
        issues.append("domain_policies.yaml missing — no domain-aware tier policy")

    # CLAUDE.md (constitution) protected from direct writes
    if _exists(security_yaml):
        if "CLAUDE.md" in security_yaml.read_text(encoding="utf-8"):
            findings.append("Constitution protected: CLAUDE.md in write denylist")
        else:
            issues.append("Constitution NOT protected: CLAUDE.md not in write denylist")

    score = max(0.0, 10.0 - len(issues) * 2.0)
    return score, findings, issues


# ---------------------------------------------------------------------------
# Category 7: Cost Efficiency
# ---------------------------------------------------------------------------
def audit_cost_efficiency() -> tuple[float, list[str], list[str]]:
    """Token budget, domain policies, utility function, forecasting."""
    findings: list[str] = []
    issues: list[str] = []

    core = ROOT / "core"

    cost_modules = {
        "budget_manager.py": "token/time budget allocation",
        "utility.py": "expected utility scoring (EU = p*reward - risk)",
        "forecast.py": "linear trend forecasting (proactive optimization)",
        "strategy_generator.py": "K-candidate DAG exploration (best plan selection)",
    }
    for module, desc in cost_modules.items():
        p = core / module
        if _exists(p) and _py_parses(p):
            findings.append(f"Cost module: {module} ({desc})")
        else:
            issues.append(f"Missing: {module} ({desc})")

    # Domain policies (only run expensive strategies where needed)
    if _exists(ROOT / "policies" / "domain_policies.yaml"):
        findings.append("Domain policies: cost-adjusted tier per task type")
    else:
        issues.append("domain_policies.yaml missing — no cost-tiered routing")

    # keyword-TFIDF backend (better than SHA, cheaper than neural)
    representations = core / "representations.py"
    if _exists(representations):
        content = representations.read_text(encoding="utf-8")
        if "keyword-tfidf" in content:
            findings.append("representations: keyword-TFIDF backend (real semantic, stdlib-only)")
        else:
            issues.append("representations: no semantic backend (only SHA placeholder)")
    else:
        issues.append("representations.py missing")

    score = max(0.0, 10.0 - len(issues) * 2.0)
    return score, findings, issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("Tool Coverage",       audit_tool_coverage),
    ("Context Efficiency",  audit_context_efficiency),
    ("Quality Gates",       audit_quality_gates),
    ("Memory Persistence",  audit_memory_persistence),
    ("Eval Coverage",       audit_eval_coverage),
    ("Security Guardrails", audit_security_guardrails),
    ("Cost Efficiency",     audit_cost_efficiency),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Agentic OS harness quality audit")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    parser.add_argument("--category", type=int, help="Run single category (1-7)")
    parser.add_argument("--threshold", type=float, default=0.0,
                        help="Exit 1 if overall score < threshold")
    args = parser.parse_args()

    results = {}
    cats = CATEGORIES
    if args.category:
        idx = args.category - 1
        if 0 <= idx < len(CATEGORIES):
            cats = [CATEGORIES[idx]]
        else:
            print(f"Invalid category {args.category} (1-{len(CATEGORIES)})", file=sys.stderr)
            return 1

    for name, fn in cats:
        score, findings, issues = fn()
        results[name] = {
            "score": round(score, 1),
            "findings": findings,
            "issues": issues,
        }

    scores = [v["score"] for v in results.values()]
    overall = round(sum(scores) / len(scores), 1) if scores else 0.0

    output = {
        "overall": overall,
        "categories": results,
        "target": 8.0,
        "verdict": "PASS" if overall >= 8.0 else ("WARN" if overall >= 6.0 else "FAIL"),
    }

    print(json.dumps(output, indent=2))

    if not args.json:
        print("\n=== Agentic OS Harness Audit ===", file=sys.stderr)
        for name, data in results.items():
            bar = "#" * int(data["score"]) + "." * (10 - int(data["score"]))
            print(f"  [{bar}] {data['score']:4.1f}/10  {name}", file=sys.stderr)
            for issue in data["issues"]:
                print(f"    ✗ {issue}", file=sys.stderr)
        print(f"\n  Overall: {overall}/10  ({output['verdict']})", file=sys.stderr)
        if overall < 8.0:
            all_issues = [i for d in results.values() for i in d["issues"]]
            print(f"\n  Top issues to address ({len(all_issues)} total):", file=sys.stderr)
            for issue in all_issues[:5]:
                print(f"    → {issue}", file=sys.stderr)

    if args.threshold and overall < args.threshold:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
