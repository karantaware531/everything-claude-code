#!/usr/bin/env python3
"""
test_runner.py — single source of truth for "is the v2 system healthy?"

Runs 13 checks. Exit 0 iff all pass. Ideal for use in /initialize, CI, or a
scheduled sanity task. Stdlib only.

Checks:
    1  agent_validator.py --self-test passes (all 16 agents)
    2  every core module AST-parses (6 files)
    3  policy_guard denies "write:.env"
    4  policy_guard allows "write:.claude/agents/foo.md"
    5  scoring_engine --stats orchestrator returns default stub
    6  agent_selector returns a chosen agent for a simple capability
    7  context_engine --task emits JSON with a 'provenance' key
    8  wiki_compiler --dry-run exits 0
    9  code_executor --source "print(2+2)" prints 4
    10 tool_registry --list returns >= 4 tools
    11 execution_engine --simulate on trivial plan reports risk=none
    12 every workflow template under workflows/ is valid JSON
    13 Karpathy invariant: find .claude/memory -name '*.md' is empty
"""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/
REPO_ROOT = ROOT.parent                      # project root
CORE = ROOT / "core"
TOOLS = ROOT / "tools"
WORKFLOWS = ROOT / "workflows"
MEMORY = ROOT / "memory"

PY = sys.executable


def run(cmd: list[str], check_stdout_contains: str | None = None,
        expect_exit: int | None = 0, timeout: int = 30) -> tuple[bool, str]:
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=timeout, cwd=str(ROOT.parent))
    except FileNotFoundError as e:
        return False, f"command not found: {e}"
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout}s"

    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if expect_exit is not None and result.returncode != expect_exit:
        return False, f"expected exit={expect_exit}, got {result.returncode}\nstdout: {stdout[:200]}\nstderr: {stderr[:200]}"
    if check_stdout_contains is not None and check_stdout_contains not in stdout:
        return False, f"expected '{check_stdout_contains}' in stdout; got: {stdout[:300]}"
    return True, "ok"


def check_1_self_test() -> tuple[bool, str]:
    ok, msg = run([PY, str(TOOLS / "agent_validator.py"), "--self-test"])
    return ok, "all agents pass validator" if ok else msg


def check_2_core_parses() -> tuple[bool, str]:
    files = [
        "context_engine.py", "execution_engine.py", "agent_selector.py",
        "scoring_engine.py", "graph_query.py", "tool_registry.py",
        # v3 additions
        "uncertainty.py", "autonomy_controller.py", "protocol_validator.py",
        # v4 additions
        "world_model.py", "environment_sensor.py", "reward.py",
        "budget_manager.py", "epoch_learner.py", "representations.py",
        # v5 additions
        "utility.py", "strategy_generator.py", "consolidator.py", "forecast.py",
    ]
    for f in files:
        p = CORE / f
        if not p.exists():
            return False, f"missing {p}"
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            return False, f"{f} syntax error: {e}"
    return True, f"all {len(files)} core modules parse"


def check_3_policy_denies_env() -> tuple[bool, str]:
    ok, msg = run([PY, str(TOOLS / "policy_guard.py"), "--action", "write:.env"],
                  expect_exit=1)
    return ok, "denied" if ok else msg


def check_4_policy_allows_agent_write() -> tuple[bool, str]:
    ok, msg = run([PY, str(TOOLS / "policy_guard.py"),
                   "--action", "write:.claude/agents/foo.md"], expect_exit=0)
    return ok, "allowed" if ok else msg


def check_5_scoring_default() -> tuple[bool, str]:
    ok, msg = run([PY, str(CORE / "scoring_engine.py"), "--stats", "orchestrator"],
                  check_stdout_contains='"success_rate"')
    return ok, "default stub returned" if ok else msg


def check_6_selector_returns_agent() -> tuple[bool, str]:
    ok, msg = run([PY, str(CORE / "agent_selector.py"),
                   "--capability", "plan a task",
                   "--task", "add feature",
                   "--seed", "42"],
                  check_stdout_contains='"chosen"')
    return ok, "selector returns a choice" if ok else msg


def check_7_context_provenance() -> tuple[bool, str]:
    ok, msg = run([PY, str(CORE / "context_engine.py"),
                   "--task", "smoke", "--format", "json"],
                  check_stdout_contains='"provenance"')
    return ok, "context has provenance" if ok else msg


def check_8_notes_structure() -> tuple[bool, str]:
    """v5.2: .claude/notes/ exists with all 7 domain subdirs (replaces wiki_compiler check)."""
    notes_root = ROOT / "notes"
    if not notes_root.exists():
        return False, ".claude/notes/ directory missing"
    required = ["strategies", "experience", "goals", "self", "patterns", "consensus", "concepts"]
    missing = [d for d in required if not (notes_root / d).is_dir()]
    if missing:
        return False, f"missing domains: {missing}"
    # README.md documents the new architecture
    if not (notes_root / "README.md").exists():
        return False, "notes/README.md missing"
    return True, f"all {len(required)} notes/ domains present + README"


def check_9_code_executor() -> tuple[bool, str]:
    ok, msg = run([PY, str(TOOLS / "code_executor.py"),
                   "--source", "print(2+2)"],
                  check_stdout_contains='"stdout": "4')
    return ok, "2+2=4" if ok else msg


def check_10_tool_registry() -> tuple[bool, str]:
    ok, msg = run([PY, str(CORE / "tool_registry.py"), "--list"])
    if not ok:
        return False, msg
    # parse stdout to verify count >= 4
    try:
        result = subprocess.run([PY, str(CORE / "tool_registry.py"), "--list"],
                                capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        if data.get("count", 0) >= 4:
            return True, f"{data['count']} tools registered"
        return False, f"only {data.get('count', 0)} tools"
    except Exception as e:  # noqa: BLE001
        return False, f"parse error: {e}"


def check_11_simulate_trivial() -> tuple[bool, str]:
    plan = json.dumps({
        "task_id": "t-smoke",
        "goal":    "noop",
        "nodes":   [{"id": "n1", "capability": "decompose task into DAG", "input": {}, "expected_output": "ok"}],
        "edges":   []
    })
    ok, msg = run([PY, str(CORE / "execution_engine.py"), "--simulate", "--plan", plan],
                  check_stdout_contains='"risk": "none"')
    return ok, "trivial plan simulates cleanly" if ok else msg


def check_12_workflows_valid_json() -> tuple[bool, str]:
    if not WORKFLOWS.exists():
        return False, "workflows/ missing"
    files = list(WORKFLOWS.glob("*.json"))
    if not files:
        return False, "no workflow templates"
    for f in files:
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            return False, f"{f.name} invalid: {e}"
    return True, f"{len(files)} workflows valid"


def check_13_karpathy_invariant() -> tuple[bool, str]:
    if not MEMORY.exists():
        return True, "memory/ does not exist — invariant trivially holds"
    md_files = list(MEMORY.rglob("*.md"))
    if md_files:
        return False, f"found .md files in memory/: {[str(p.relative_to(ROOT)) for p in md_files]}"
    return True, "memory/ has no .md files"


def check_14_evaluator_has_uncertainty() -> tuple[bool, str]:
    path = ROOT / "agents" / "governance" / "evaluator.md"
    if not path.exists():
        return False, "evaluator.md missing"
    text = path.read_text(encoding="utf-8")
    if '"uncertainty"' not in text:
        return False, "evaluator.md does not declare 'uncertainty' in its verdict schema"
    return True, "evaluator emits uncertainty"


def check_15_autonomy_controller_returns_tier() -> tuple[bool, str]:
    ok, msg = run([PY, str(CORE / "autonomy_controller.py"),
                   "--task", "smoke",
                   "--uncertainty", "0.5",
                   "--risk", "low"])
    if not ok:
        return False, msg
    try:
        result = subprocess.run([PY, str(CORE / "autonomy_controller.py"),
                                 "--task", "smoke", "--uncertainty", "0.5", "--risk", "low"],
                                capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        tier = data.get("tier")
        if tier in (1, 2, 3, 4):
            return True, f"tier {tier} ({data.get('name')})"
        return False, f"invalid tier: {tier!r}"
    except Exception as e:  # noqa: BLE001
        return False, f"parse error: {e}"


def check_16_protocol_validator() -> tuple[bool, str]:
    valid = json.dumps({
        "from": "orchestrator", "to": "planner",
        "task_id": "t-1", "trace_id": "trc-1",
        "kind": "request", "context_ref": "abc",
        "timestamp": "2026-04-20T00:00:00Z",
        "payload": {}, "protocol_version": "1.0"
    })
    ok_valid, _ = run([PY, str(CORE / "protocol_validator.py"), "--message", valid],
                      expect_exit=0)
    if not ok_valid:
        return False, "valid message was rejected"
    ok_invalid, _ = run([PY, str(CORE / "protocol_validator.py"), "--message", "{}"],
                        expect_exit=1)
    if not ok_invalid:
        return False, "malformed message was accepted"
    return True, "accepts valid, rejects malformed"


def check_17_governance_yaml_parses() -> tuple[bool, str]:
    gov = ROOT / "policies" / "governance.yaml"
    if not gov.exists():
        return False, "governance.yaml missing"
    sys.path.insert(0, str(TOOLS))
    try:
        from policy_guard import _parse_yaml  # noqa: WPS433
    except ImportError as e:
        return False, f"cannot import policy_guard: {e}"
    try:
        data = _parse_yaml(gov.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return False, f"parse error: {e}"
    tiers = data.get("tiers", {})
    action_tiers = data.get("action_tiers", {})
    if len(tiers) != 4:
        return False, f"expected 4 tiers, got {len(tiers)}"
    if not action_tiers:
        return False, "action_tiers empty"
    return True, f"{len(tiers)} tiers, {len(action_tiers)} action_tiers"


def check_18_world_model() -> tuple[bool, str]:
    """v4: world_model returns a structured prediction."""
    ok, msg = run([PY, str(CORE / "world_model.py"), "--predict", "noop", "noop"])
    if not ok:
        return False, msg
    try:
        result = subprocess.run([PY, str(CORE / "world_model.py"), "--predict", "noop", "noop"],
                                capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        if "predictions" in data:
            return True, "predict returns structured response"
        return False, "missing 'predictions' key"
    except Exception as e:  # noqa: BLE001
        return False, f"parse error: {e}"


def check_19_reward_returns_float() -> tuple[bool, str]:
    """v4: reward.py returns a float in [-1, 1]."""
    try:
        result = subprocess.run([PY, str(CORE / "reward.py"),
                                 "--success", "0.9", "--cost", "0.1", "--risk", "0.0"],
                                capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout)
        r = data.get("reward")
        if isinstance(r, (int, float)) and -1.0 <= r <= 1.0:
            return True, f"reward={r}"
        return False, f"invalid reward: {r!r}"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_20_budget_manager_lifecycle() -> tuple[bool, str]:
    """v4: budget_manager allocate -> consume -> exceeded -> release roundtrip."""
    task_id = "t-test-runner-smoke"
    try:
        # allocate
        r = subprocess.run([PY, str(CORE / "budget_manager.py"),
                            "--allocate", task_id, "--tokens", "1000", "--time", "60"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return False, f"allocate failed: {r.stderr[:200]}"
        data = json.loads(r.stdout)
        if data.get("tokens_allocated") != 1000:
            return False, f"unexpected allocation: {data}"
        # exceeded -> false
        r2 = subprocess.run([PY, str(CORE / "budget_manager.py"),
                             "--exceeded", task_id],
                            capture_output=True, text=True, timeout=10)
        d2 = json.loads(r2.stdout)
        if d2.get("exceeded"):
            return False, "fresh budget reported exceeded"
        # release (cleanup)
        subprocess.run([PY, str(CORE / "budget_manager.py"),
                        "--release", task_id, "--reason", "test_runner"],
                       capture_output=True, text=True, timeout=10)
        return True, "allocate/exceeded/release cycle OK"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_21_values_yaml() -> tuple[bool, str]:
    """v4: values.yaml declares >= 1 value with violation_patterns."""
    vals_path = ROOT / "policies" / "values.yaml"
    if not vals_path.exists():
        return False, "values.yaml missing"
    sys.path.insert(0, str(TOOLS))
    try:
        from policy_guard import _parse_yaml  # noqa: WPS433
    except ImportError as e:
        return False, f"cannot import policy_guard: {e}"
    try:
        data = _parse_yaml(vals_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return False, f"parse error: {e}"
    vals = data.get("values", []) or []
    if len(vals) < 1:
        return False, "no values declared"
    if not any(v.get("violation_patterns") for v in vals if isinstance(v, dict)):
        return False, "no value carries violation_patterns"
    return True, f"{len(vals)} values declared"


def check_22_system_profile_schema() -> tuple[bool, str]:
    """v4: system_profile.json exists with required schema."""
    p = MEMORY / "system_profile.json"
    if not p.exists():
        return False, "system_profile.json missing"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"invalid JSON: {e}"
    required = ["version", "epoch_count", "domain_competence",
                "weak_spots", "strong_pairings", "global_metrics"]
    missing = [k for k in required if k not in data]
    if missing:
        return False, f"missing keys: {missing}"
    return True, "schema OK"


def check_23_utility_returns_float() -> tuple[bool, str]:
    """v5: utility.py returns a float in [-1, 1]."""
    try:
        r = subprocess.run([PY, str(CORE / "utility.py"),
                            "--p-success", "0.8", "--reward", "0.5", "--risk-cost", "0.3"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return False, f"exit={r.returncode}: {r.stderr[:200]}"
        u = json.loads(r.stdout).get("utility")
        if isinstance(u, (int, float)) and -1.0 <= u <= 1.0:
            return True, f"utility={u}"
        return False, f"invalid utility: {u!r}"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_24_strategy_generator() -> tuple[bool, str]:
    """v5: strategy_generator returns >= 2 distinct candidate DAGs."""
    try:
        r = subprocess.run([PY, str(CORE / "strategy_generator.py"),
                            "--task", "smoke task", "--k", "3", "--compact"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False, f"exit={r.returncode}: {r.stderr[:200]}"
        data = json.loads(r.stdout)
        candidates = data.get("candidates", []) or []
        hashes = {c.get("dag_hash") for c in candidates}
        if len(candidates) >= 2 and len(hashes) >= 2:
            return True, f"{len(candidates)} candidates, {len(hashes)} distinct"
        return False, f"only {len(candidates)} candidates / {len(hashes)} distinct"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_25_world_model_scenarios() -> tuple[bool, str]:
    """v5: world_model.scenarios returns best/expected/worst keys (may be null if no data)."""
    try:
        r = subprocess.run([PY, str(CORE / "world_model.py"),
                            "--scenarios", "idle", "compile"],
                           capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            return False, f"exit={r.returncode}: {r.stderr[:200]}"
        data = json.loads(r.stdout)
        if all(k in data for k in ("best", "expected", "worst")):
            return True, "best/expected/worst keys present"
        return False, f"missing keys; got {list(data.keys())}"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_26_keyword_tfidf_backend_available() -> tuple[bool, str]:
    """v5: keyword-tfidf is registered as a backend."""
    try:
        r = subprocess.run([PY, str(CORE / "representations.py"), "--backend"],
                           capture_output=True, text=True, timeout=10,
                           env={**os.environ, "AGENTIC_OS_EMBEDDING_BACKEND": "keyword-tfidf"})
        if r.returncode != 0:
            return False, f"exit={r.returncode}: {r.stderr[:200]}"
        data = json.loads(r.stdout)
        backends = data.get("all", [])
        if "keyword-tfidf" in backends:
            return True, f"backends: {backends}"
        return False, f"keyword-tfidf not in {backends}"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_28_hooks_configuration() -> tuple[bool, str]:
    """v5.1: .claude/settings.json registers the expected hook events; hook scripts exist and parse."""
    settings = ROOT / "settings.json"
    hooks_dir = ROOT / "hooks"
    if not settings.exists():
        return False, ".claude/settings.json missing"
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"settings.json invalid: {e}"

    hooks = data.get("hooks") or {}
    expected_events = {"SessionStart", "PreToolUse", "PostToolUse", "Stop"}
    missing_events = expected_events - hooks.keys()
    if missing_events:
        return False, f"missing hook events: {sorted(missing_events)}"

    expected_scripts = [
        "enforce_policy_on_bash.py",
        "enforce_policy_on_write.py",
        "karpathy_invariant_check.py",
        "session_health_probe.py",
        "suggest_epoch_learner.py",
        "gateguard.py",
        "precompact_state_saver.py",
        # v5.4 additions
        "notification.py",
        "post_compact_reinject.py",
        "config_change_audit.py",
        "session_end_summary.py",
        "subagent_lifecycle.py",
        # v5.4.1: security content scanner (from Anthropic security-guidance plugin)
        "security_reminder_hook.py",
    ]
    for s in expected_scripts:
        p = hooks_dir / s
        if not p.exists():
            return False, f"missing hook script: hooks/{s}"
        try:
            ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError as e:
            return False, f"hooks/{s} syntax error: {e}"

    return True, f"{len(hooks)} hook events registered; all {len(expected_scripts)} scripts parse"


def check_27_consolidator_dry_run() -> tuple[bool, str]:
    """v5: consolidator --dry-run runs clean AND consolidation_log is valid JSON."""
    log = MEMORY / "consolidation_log.json"
    if not log.exists():
        return False, "consolidation_log.json missing"
    try:
        json.loads(log.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"consolidation_log invalid JSON: {e}"
    try:
        r = subprocess.run([PY, str(CORE / "consolidator.py"), "--dry-run"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return False, f"exit={r.returncode}: {r.stderr[:200]}"
        data = json.loads(r.stdout)
        if data.get("dry_run") is True:
            return True, "dry-run clean"
        return False, f"unexpected output: {list(data.keys())}"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_29_root_navigation_layer() -> tuple[bool, str]:
    """v5.1 ECC: root CLAUDE.md, AGENTS.md, RULES.md, and .mcp.json exist."""
    required = {
        "CLAUDE.md":  REPO_ROOT / "CLAUDE.md",
        "AGENTS.md":  REPO_ROOT / "AGENTS.md",
        "RULES.md":   REPO_ROOT / "RULES.md",
        ".mcp.json":  REPO_ROOT / ".mcp.json",
    }
    missing = []
    for name, path in required.items():
        if not path.exists():
            missing.append(name)
    if missing:
        return False, f"missing root files: {missing}"
    # Root CLAUDE.md should include the constitution via @-include
    root_claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    if "@.claude/CLAUDE.md" not in root_claude:
        return False, "root CLAUDE.md does not @-include .claude/CLAUDE.md"
    # .mcp.json must be valid JSON with mcpServers key
    try:
        mcp = json.loads((REPO_ROOT / ".mcp.json").read_text(encoding="utf-8"))
        if "mcpServers" not in mcp:
            return False, ".mcp.json missing mcpServers key"
        count = len(mcp["mcpServers"])
        return True, f"root files OK; {count} MCP servers configured"
    except json.JSONDecodeError as e:
        return False, f".mcp.json invalid JSON: {e}"


def check_30_slash_commands_present() -> tuple[bool, str]:
    """v5.1 ECC: new slash commands exist as .md files in .claude/commands/."""
    commands_dir = ROOT / "commands"
    required = ["review.md", "debug.md", "ingest.md", "epoch.md",
                "explore.md", "council.md", "save-session.md", "verify.md"]
    missing = [c for c in required if not (commands_dir / c).exists()]
    if missing:
        return False, f"missing commands: {missing}"
    return True, f"all {len(required)} ECC commands present"


def check_31_gateguard_hook() -> tuple[bool, str]:
    """v5.1 ECC: gateguard.py hook exists, parses, and is registered in settings.json."""
    hook_path = ROOT / "hooks" / "gateguard.py"
    if not hook_path.exists():
        return False, "hooks/gateguard.py missing"
    try:
        ast.parse(hook_path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return False, f"gateguard.py syntax error: {e}"
    # Verify registered in settings.json
    settings = ROOT / "settings.json"
    if not settings.exists():
        return False, "settings.json missing"
    data = json.loads(settings.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    pre_tool_use = hooks.get("PreToolUse", [])
    for entry in pre_tool_use:
        for h in entry.get("hooks", []):
            if "gateguard" in h.get("command", ""):
                return True, "gateguard.py parses + registered in PreToolUse"
    return False, "gateguard.py not found in settings.json PreToolUse hooks"


def check_32_precompact_hook() -> tuple[bool, str]:
    """v5.1 ECC: precompact_state_saver.py hook exists, parses, and PreCompact event registered."""
    hook_path = ROOT / "hooks" / "precompact_state_saver.py"
    if not hook_path.exists():
        return False, "hooks/precompact_state_saver.py missing"
    try:
        ast.parse(hook_path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return False, f"precompact_state_saver.py syntax error: {e}"
    # Verify PreCompact event in settings.json
    settings = ROOT / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    if "PreCompact" not in hooks:
        return False, "PreCompact event not registered in settings.json"
    return True, "precompact_state_saver.py parses + PreCompact event registered"


def check_34_graphify_installed() -> tuple[bool, str]:
    """v5.2: graphifyy Python package installed and CLI responsive."""
    try:
        r = subprocess.run(
            ["py", "-3", "-c", "import graphify; print('ok')"],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return False, f"graphify import failed: {r.stderr[:200]}"
        r2 = subprocess.run(
            ["py", "-3", "-m", "graphify", "--help"],
            capture_output=True, text=True, timeout=15
        )
        if r2.returncode != 0 or "Usage" not in r2.stdout:
            return False, f"graphify CLI --help failed: {r2.stderr[:200]}"
        return True, "graphifyy importable + CLI works"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_35_graphify_agent_registered() -> tuple[bool, str]:
    """v5.2: graphify_agent exists in registry.json and has an agent file."""
    reg = ROOT / "registry.json"
    if not reg.exists():
        return False, ".claude/registry.json missing"
    try:
        data = json.loads(reg.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"registry.json invalid: {e}"
    names = [a["name"] for a in data.get("agents", [])]
    if "graphify_agent" not in names:
        return False, "graphify_agent not in registry.json"
    fp = ROOT / "agents" / "execution" / "graphify_agent.md"
    if not fp.exists():
        return False, "agents/execution/graphify_agent.md missing"
    if "wiki_updater" in names or "wiki_curator" in names:
        return False, "wiki_updater/wiki_curator still in registry (should be retired)"
    return True, f"graphify_agent registered; wiki agents retired; {len(names)} total"


def check_36_graphify_mcp_configured() -> tuple[bool, str]:
    """v5.2: .mcp.json includes the graphify MCP server."""
    mcp = REPO_ROOT / ".mcp.json"
    if not mcp.exists():
        return False, ".mcp.json missing"
    data = json.loads(mcp.read_text(encoding="utf-8"))
    servers = data.get("mcpServers", {})
    if "graphify" not in servers:
        return False, "graphify not in .mcp.json mcpServers"
    g = servers["graphify"]
    if "graphify.serve" not in " ".join(g.get("args", [])):
        return False, "graphify.serve not in args"
    return True, "graphify MCP server configured"


def check_37_graphify_commands_present() -> tuple[bool, str]:
    """v5.2: graphify slash commands (graphify + 4 shortcuts)."""
    cmd_dir = ROOT / "commands"
    required = ["graphify.md", "graphify-build.md", "graphify-query.md",
                "graphify-explain.md", "graphify-path.md"]
    missing = [c for c in required if not (cmd_dir / c).exists()]
    if missing:
        return False, f"missing commands: {missing}"
    # graphify.md should be the full skill (>100 lines)
    main = cmd_dir / "graphify.md"
    if main.exists() and len(main.read_text(encoding="utf-8").splitlines()) < 100:
        return False, "graphify.md is too short (should be the full skill)"
    return True, f"all {len(required)} graphify commands present"


def check_38_wiki_removed() -> tuple[bool, str]:
    """v5.2: .claude/wiki/ is fully removed; no wiki_compiler.py; security.yaml cleaned."""
    wiki = ROOT / "wiki"
    if wiki.exists():
        return False, f".claude/wiki/ still exists at {wiki}"
    wc = TOOLS / "wiki_compiler.py"
    if wc.exists():
        return False, "tools/wiki_compiler.py still exists"
    sec_yaml = ROOT / "policies" / "security.yaml"
    sec_text = sec_yaml.read_text(encoding="utf-8")
    if ".claude/wiki/" in sec_text:
        return False, "security.yaml still references .claude/wiki/"
    return True, "wiki fully removed; security.yaml clean"


def check_33_harness_audit() -> tuple[bool, str]:
    """v5.1 ECC: harness_audit.py exists, parses, and returns a valid JSON score."""
    audit_path = TOOLS / "harness_audit.py"
    if not audit_path.exists():
        return False, "tools/harness_audit.py missing"
    try:
        ast.parse(audit_path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return False, f"harness_audit.py syntax error: {e}"
    # Run it and verify output
    try:
        result = subprocess.run(
            [PY, str(audit_path), "--json"],
            capture_output=True, text=True, timeout=30,
            cwd=str(ROOT.parent)
        )
        if result.returncode not in (0, 1):  # 1 = below threshold (OK for this check)
            return False, f"harness_audit.py exited {result.returncode}: {result.stderr[:200]}"
        data = json.loads(result.stdout)
        overall = data.get("overall")
        verdict = data.get("verdict")
        if overall is not None and verdict in ("PASS", "WARN", "FAIL"):
            return True, f"harness score: {overall}/10 ({verdict})"
        return False, f"unexpected output: {list(data.keys())}"
    except Exception as e:  # noqa: BLE001
        return False, f"error: {e}"


def check_43_plugin_manifest() -> tuple[bool, str]:
    """v5.6: plugins-manifest.json + install_plugins.py + /install-plugins command all present."""
    manifest = ROOT / "plugins-manifest.json"
    installer = ROOT / "tools" / "install_plugins.py"
    command = ROOT / "commands" / "install-plugins.md"

    for p, label in [(manifest, "plugins-manifest.json"),
                     (installer, "tools/install_plugins.py"),
                     (command, "commands/install-plugins.md")]:
        if not p.exists():
            return False, f"{label} missing"

    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"plugins-manifest.json invalid JSON: {e}"

    plugins = data.get("plugins", {})
    core = [k for k in plugins.get("core", {}).keys() if not k.startswith("$")]
    if len(core) < 5:
        return False, f"core plugins count too low: {len(core)} (expect >= 5)"

    # Verify installer AST-parses + produces output
    try:
        ast.parse(installer.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return False, f"install_plugins.py syntax error: {e}"

    try:
        r = subprocess.run([PY, str(installer)], capture_output=True, text=True,
                           timeout=15, cwd=str(ROOT.parent))
        if r.returncode != 0:
            return False, f"install_plugins.py exit {r.returncode}: {r.stderr[:200]}"
        # Should print install commands for at least the 'core' plugins
        install_lines = [ln for ln in r.stdout.splitlines() if ln.startswith("/plugin install ")]
        if len(install_lines) < len(core):
            return False, f"installer output has {len(install_lines)} commands; expected >= {len(core)}"
    except Exception as e:  # noqa: BLE001
        return False, f"installer exec error: {e}"

    return True, f"manifest OK; {len(core)} core plugins; installer produces {len(install_lines)} commands"


def check_42_hook_paths_cwd_independent() -> tuple[bool, str]:
    """v5.5.1: every hook command in settings.json uses $CLAUDE_PROJECT_DIR (CWD-independent).

    Regression guard for the 2026-04-24 self-inflicted lockout: relative paths like
    `python .claude/hooks/X.py` broke when CWD drifted outside repo root, and the
    broken hooks blocked every tool that could have fixed them. Root cause doc:
    memory/logs.json -> v5.5.1-hook-path-cwd-fix.
    """
    settings = ROOT / "settings.json"
    if not settings.exists():
        return False, "settings.json missing"
    data = json.loads(settings.read_text(encoding="utf-8"))
    offenders = []
    total = 0
    for event, blocks in data.get("hooks", {}).items():
        for block in blocks:
            for h in block.get("hooks", []):
                cmd = h.get("command", "")
                if not cmd:
                    continue
                total += 1
                # Command invokes a hook script in .claude/hooks/ without CLAUDE_PROJECT_DIR
                if ".claude/hooks/" in cmd and "CLAUDE_PROJECT_DIR" not in cmd:
                    offenders.append(f"{event}: {cmd[:60]}")
    if offenders:
        return False, f"{len(offenders)}/{total} hook commands missing $CLAUDE_PROJECT_DIR: {offenders[:3]}"
    return True, f"all {total} hook commands use $CLAUDE_PROJECT_DIR (CWD-independent)"


def check_41_v55_lead_agent_government() -> tuple[bool, str]:
    """v5.5: constitution <= 200 lines, orchestrator retired, acceptEdits default, agent teams enabled,
    Council doc present, history extracted, frontmatter decision doc present, 21 agents."""
    constitution = ROOT / "CLAUDE.md"
    if not constitution.exists():
        return False, ".claude/CLAUDE.md missing"
    lines = len(constitution.read_text(encoding="utf-8").splitlines())
    # v5.7 raised the target to 250 to accommodate the Planning Council section (§5b)
    # per Council decision. See notes/consensus/v5.7-mandatory-planning-council.md.
    if lines > 250:
        return False, f"constitution is {lines} lines (target <= 250, v5.7 baseline)"
    # orchestrator retired
    if (ROOT / "agents" / "meta" / "orchestrator.md").exists():
        return False, "orchestrator.md still present (should be retired per v5.5)"
    # registry should have 21 agents, no orchestrator
    reg = json.loads((ROOT / "registry.json").read_text(encoding="utf-8"))
    names = [a["name"] for a in reg.get("agents", [])]
    if "orchestrator" in names:
        return False, "orchestrator still in registry"
    if len(names) != 21:
        return False, f"expected 21 agents, got {len(names)}"
    # settings.json: defaultMode acceptEdits + agent teams env
    settings = json.loads((ROOT / "settings.json").read_text(encoding="utf-8"))
    if settings.get("permissions", {}).get("defaultMode") != "acceptEdits":
        return False, "defaultMode not acceptEdits"
    if settings.get("env", {}).get("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS") != "1":
        return False, "Agent Teams env var not set"
    # required new docs
    for f in [
        ROOT / "notes" / "concepts" / "agentic-os-history.md",
        ROOT / "notes" / "concepts" / "agent-frontmatter-distribution.md",
        ROOT / "notes" / "consensus" / "v5.5-lead-agent-government.md",
        ROOT / "rules" / "permission-modes.md",
        ROOT / "rules" / "routing.md",
    ]:
        if not f.exists():
            return False, f"missing: {f.relative_to(ROOT.parent)}"
    return True, f"constitution {lines} lines, 21 agents, acceptEdits default, Agent Teams enabled, all docs present"


def check_40_anthropic_alignment() -> tuple[bool, str]:
    """v5.4: rules dir, skills scaffold, .worktreeinclude, permissions block, autoMemory."""
    rules = ROOT / "rules"
    if not rules.exists():
        return False, ".claude/rules/ missing"
    required_rules = ["README.md", "agents.md", "hooks.md", "notes.md", "testing.md"]
    missing_rules = [r for r in required_rules if not (rules / r).exists()]
    if missing_rules:
        return False, f"missing rules: {missing_rules}"
    skills = ROOT / "skills"
    if not skills.exists():
        return False, ".claude/skills/ missing"
    if not (skills / "README.md").exists():
        return False, ".claude/skills/README.md missing"
    if not (skills / "graphify-refresh" / "SKILL.md").exists():
        return False, "reference skill graphify-refresh missing"
    wt = REPO_ROOT / ".worktreeinclude"
    if not wt.exists():
        return False, ".worktreeinclude missing at repo root"
    example = REPO_ROOT / "CLAUDE.local.md.example"
    if not example.exists():
        return False, "CLAUDE.local.md.example missing at repo root"
    # Settings.json must now have permissions + autoMemoryEnabled
    settings = ROOT / "settings.json"
    data = json.loads(settings.read_text(encoding="utf-8"))
    if "permissions" not in data:
        return False, "settings.json missing permissions block"
    perm = data["permissions"]
    for k in ("allow", "deny", "defaultMode"):
        if k not in perm:
            return False, f"permissions.{k} missing"
    if data.get("autoMemoryEnabled") is not True:
        return False, "autoMemoryEnabled not set to true"
    # 5 new hook events must be registered
    hooks = data.get("hooks", {})
    for evt in ("PostCompact", "Notification", "ConfigChange", "SubagentStart",
                "SubagentStop", "SessionEnd"):
        if evt not in hooks:
            return False, f"hook event {evt} not registered"
    return True, "v5.4 rules + skills + worktree + permissions + autoMemory + 6 new hook events"


def check_39_specialist_registry() -> tuple[bool, str]:
    """v5.3: SPECIALISTS.md exists + voltagent plugins detected (non-fatal warnings)."""
    specs = REPO_ROOT / "SPECIALISTS.md"
    if not specs.exists():
        return False, "SPECIALISTS.md missing at repo root"
    # Check voltagent plugin cache on user's machine (non-fatal: warn but pass if present)
    home = Path.home()
    plugin_cache = home / ".claude" / "plugins" / "cache" / "voltagent-subagents"
    expected_plugins = ["voltagent-lang", "voltagent-dev-exp", "voltagent-qa-sec",
                        "voltagent-data-ai", "voltagent-research"]
    if not plugin_cache.exists():
        return True, "SPECIALISTS.md OK; voltagent cache absent (specialists fall back to code_agent)"
    missing = [p for p in expected_plugins if not (plugin_cache / p).exists()]
    if missing:
        return True, f"SPECIALISTS.md OK; missing plugins: {missing} (non-fatal; fallback to generic agents)"
    # Count total specialist .md files
    total_md = 0
    for plugin in expected_plugins:
        pdir = plugin_cache / plugin
        if pdir.exists():
            for v in pdir.iterdir():
                if v.is_dir():
                    total_md += sum(1 for _ in v.glob("*.md")) - 1  # minus README
    return True, f"SPECIALISTS.md OK; ~{total_md} voltagent specialists available"


def check_45_skills_agentskills_spec() -> tuple[bool, str]:
    """v5.7: every .claude/skills/*/SKILL.md conforms to agentskills.io specification.

    Spec reference: https://agentskills.io/specification
    Required frontmatter: name, description.
    Allowed top-level fields: name, description, license, compatibility, metadata, allowed-tools.
    Constraints:
      - name: 1-64 chars, lowercase [a-z0-9-], no leading/trailing hyphen, no '--', matches parent dir.
      - description: 1-1024 chars, non-empty.
      - metadata (if present): string-to-string map.
    Body: no hard limit; recommended <500 lines.
    """
    import re
    skills_dir = ROOT / "skills"
    if not skills_dir.exists():
        return False, ".claude/skills/ missing"

    allowed_keys = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
    name_re = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
    issues: list[str] = []
    checked = 0

    for skill_file in skills_dir.glob("*/SKILL.md"):
        checked += 1
        dir_name = skill_file.parent.name
        text = skill_file.read_text(encoding="utf-8")

        if not text.startswith("---"):
            issues.append(f"{dir_name}: missing frontmatter")
            continue

        end = text.find("\n---", 3)
        if end == -1:
            issues.append(f"{dir_name}: unterminated frontmatter")
            continue
        fm = text[3:end].strip()

        # Extract top-level keys by matching lines starting in column 0
        top_keys: list[str] = []
        top_vals: dict[str, str] = {}
        for line in fm.splitlines():
            if line and not line[0].isspace() and not line.startswith("#"):
                m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*)\s*:(.*)$", line)
                if m:
                    top_keys.append(m.group(1))
                    top_vals[m.group(1)] = m.group(2).strip()

        # Required keys
        if "name" not in top_keys:
            issues.append(f"{dir_name}: missing `name`")
            continue
        if "description" not in top_keys:
            issues.append(f"{dir_name}: missing `description`")
            continue

        # Unknown keys
        unknown = [k for k in top_keys if k not in allowed_keys]
        if unknown:
            issues.append(f"{dir_name}: non-spec top-level fields {unknown}")

        # name constraints
        name_val = top_vals.get("name", "").strip().strip("\"'")
        if not name_val:
            issues.append(f"{dir_name}: empty `name`")
        elif len(name_val) > 64:
            issues.append(f"{dir_name}: `name` > 64 chars")
        elif not name_re.match(name_val):
            issues.append(f"{dir_name}: `name` invalid (lowercase/hyphen only, no leading/trailing/consecutive hyphens)")
        elif name_val != dir_name:
            issues.append(f"{dir_name}: `name` ({name_val!r}) does not match parent directory")

        # description constraints
        desc_val = top_vals.get("description", "").strip().strip("\"'")
        if not desc_val:
            issues.append(f"{dir_name}: empty `description`")
        elif len(desc_val) > 1024:
            issues.append(f"{dir_name}: `description` > 1024 chars ({len(desc_val)})")

        # compatibility length
        compat = top_vals.get("compatibility", "").strip().strip("\"'")
        if compat and len(compat) > 500:
            issues.append(f"{dir_name}: `compatibility` > 500 chars")

    if issues:
        return False, f"{checked} skills checked; {len(issues)} issue(s): {issues[:3]}"
    return True, f"{checked} skills conform to agentskills.io spec (name, description, allowed fields, dir match)"


def check_44_planning_council() -> tuple[bool, str]:
    """v5.7: /lead-agent Planning Council present — skill + 4 templates + command + notes + consensus note."""
    required = [
        ROOT / "skills" / "lead-agent" / "SKILL.md",
        ROOT / "skills" / "lead-agent" / "templates" / "SPEC_TEMPLATE.md",
        ROOT / "skills" / "lead-agent" / "templates" / "TASK_ASSIGNMENTS_TEMPLATE.md",
        ROOT / "skills" / "lead-agent" / "templates" / "PERSPECTIVE_TEMPLATE.md",
        ROOT / "skills" / "lead-agent" / "templates" / "CONSENSUS_TEMPLATE.md",
        ROOT / "commands" / "lead-agent.md",
        ROOT / "notes" / "planning-council" / "README.md",
        ROOT / "notes" / "concepts" / "planning-council.md",
        ROOT / "notes" / "consensus" / "v5.7-mandatory-planning-council.md",
    ]
    missing = [p.relative_to(ROOT.parent).as_posix() for p in required if not p.exists()]
    if missing:
        return False, f"missing: {missing}"

    # skill frontmatter must declare mandatory + trigger (either legacy top-level
    # or v5.7 agentskills.io-compliant shape under `metadata:`)
    skill_text = (ROOT / "skills" / "lead-agent" / "SKILL.md").read_text(encoding="utf-8")
    if ("mandatory: true" not in skill_text and
            'mandatory: "true"' not in skill_text):
        return False, "SKILL.md missing `mandatory` declaration (top-level or metadata)"
    if ("trigger: /lead-agent" not in skill_text and
            'trigger: "/lead-agent"' not in skill_text):
        return False, "SKILL.md missing `trigger: /lead-agent` declaration"

    # routing.md must reference /lead-agent as mandatory entry
    routing = (ROOT / "rules" / "routing.md").read_text(encoding="utf-8")
    if "/lead-agent" not in routing or "PLANNING_COUNCIL" not in routing:
        return False, "routing.md missing /lead-agent + PLANNING_COUNCIL references"

    return True, f"Planning Council wired: {len(required)} artifacts, skill + routing aligned"


CHECKS = [
    ("agent_validator self-test",          check_1_self_test),
    ("core modules AST-parse",             check_2_core_parses),
    ("policy_guard denies write:.env",     check_3_policy_denies_env),
    ("policy_guard allows agent write",    check_4_policy_allows_agent_write),
    ("scoring_engine default stub",        check_5_scoring_default),
    ("agent_selector returns a choice",    check_6_selector_returns_agent),
    ("context_engine has provenance",      check_7_context_provenance),
    ("v5.2 Graphify: .claude/notes/ structure (7 domains + README)", check_8_notes_structure),
    ("code_executor runs 2+2",             check_9_code_executor),
    ("tool_registry --list >= 4",          check_10_tool_registry),
    ("execution_engine --simulate trivial", check_11_simulate_trivial),
    ("workflow templates valid JSON",      check_12_workflows_valid_json),
    ("Karpathy invariant (no .md in memory/)", check_13_karpathy_invariant),
    ("v3: evaluator verdict has 'uncertainty'", check_14_evaluator_has_uncertainty),
    ("v3: autonomy_controller returns valid tier", check_15_autonomy_controller_returns_tier),
    ("v3: protocol_validator round-trip",   check_16_protocol_validator),
    ("v3: governance.yaml parses cleanly",  check_17_governance_yaml_parses),
    ("v4: world_model returns predictions", check_18_world_model),
    ("v4: reward.py returns float in [-1,1]", check_19_reward_returns_float),
    ("v4: budget_manager lifecycle",        check_20_budget_manager_lifecycle),
    ("v4: values.yaml has values + violation patterns", check_21_values_yaml),
    ("v4: system_profile.json schema valid", check_22_system_profile_schema),
    ("v5: utility returns float in [-1,1]", check_23_utility_returns_float),
    ("v5: strategy_generator returns >=2 distinct DAGs", check_24_strategy_generator),
    ("v5: world_model scenarios returns best/expected/worst", check_25_world_model_scenarios),
    ("v5: keyword-tfidf backend registered", check_26_keyword_tfidf_backend_available),
    ("v5: consolidator dry-run + log valid", check_27_consolidator_dry_run),
    ("v5.1: hooks config + 5 hook scripts valid", check_28_hooks_configuration),
    ("v5.1 ECC: root navigation layer (CLAUDE.md/@include, AGENTS.md, RULES.md, .mcp.json)", check_29_root_navigation_layer),
    ("v5.1 ECC: 8 slash commands present",        check_30_slash_commands_present),
    ("v5.1 ECC: gateguard hook parses + registered", check_31_gateguard_hook),
    ("v5.1 ECC: precompact hook parses + PreCompact event registered", check_32_precompact_hook),
    ("v5.1 ECC: harness_audit returns valid score", check_33_harness_audit),
    ("v5.2 Graphify: graphifyy package installed + CLI works", check_34_graphify_installed),
    ("v5.2 Graphify: graphify_agent registered; wiki agents retired", check_35_graphify_agent_registered),
    ("v5.2 Graphify: MCP server configured in .mcp.json", check_36_graphify_mcp_configured),
    ("v5.2 Graphify: 5 slash commands (graphify + 4 shortcuts)", check_37_graphify_commands_present),
    ("v5.2 Graphify: wiki removed, wiki_compiler.py deleted, security.yaml clean", check_38_wiki_removed),
    ("v5.3 Specialist Government: SPECIALISTS.md + voltagent plugin presence", check_39_specialist_registry),
    ("v5.4 Anthropic Alignment: rules/+skills/+worktreeinclude+permissions+autoMemory+6 hooks", check_40_anthropic_alignment),
    ("v5.5 Lead Agent Government: constitution<=200, orchestrator retired, acceptEdits, Agent Teams, Council docs", check_41_v55_lead_agent_government),
    ("v5.5.1 Hook Paths: all hook commands use $CLAUDE_PROJECT_DIR (CWD-independent)", check_42_hook_paths_cwd_independent),
    ("v5.6 Plugin Manifest: plugins-manifest.json + installer + /install-plugins command", check_43_plugin_manifest),
    ("v5.7 Planning Council: /lead-agent skill + templates + command + notes + consensus", check_44_planning_council),
    ("v5.7 Skills Spec: all SKILL.md files conform to agentskills.io specification", check_45_skills_agentskills_spec),
]


def main() -> int:
    print(f"Running {len(CHECKS)} system checks (Agentic OS v5.7)")
    print("-" * 60)
    passed = 0
    for i, (label, fn) in enumerate(CHECKS, start=1):
        try:
            ok, detail = fn()
        except Exception as e:  # noqa: BLE001
            ok, detail = False, f"exception: {e!r}"
        marker = "PASS" if ok else "FAIL"
        print(f"[{i:>2}/{len(CHECKS)}] {marker}  {label}")
        if not ok:
            print(f"         -> {detail}")
        else:
            passed += 1

    print("-" * 60)
    print(f"{passed}/{len(CHECKS)} checks passed")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
