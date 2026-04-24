#!/usr/bin/env python3
"""One-shot retirement: delete LLM Wiki (v5.2 Graphify migration)."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # .claude/

# --- 1. Remove wiki_updater + wiki_curator from registry ---------------------
REGISTRY = ROOT / "registry.json"
data = json.loads(REGISTRY.read_text(encoding="utf-8"))
before = len(data["agents"])
retire = {"wiki_updater", "wiki_curator"}
data["agents"] = [a for a in data["agents"] if a["name"] not in retire]
after = len(data["agents"])

# Record retirement in agent_history.json ({"version":1,"entries":[...]})
history_path = ROOT / "memory" / "agent_history.json"
try:
    history = json.loads(history_path.read_text(encoding="utf-8"))
    if not isinstance(history, dict):
        history = {"version": 1, "entries": []}
except Exception:
    history = {"version": 1, "entries": []}
history.setdefault("entries", [])
now = datetime.now(timezone.utc).isoformat()
for name in retire:
    history["entries"].append({
        "agent": name,
        "task_id": "v5.2-graphify-migration",
        "timestamp": now,
        "event": "deprecated",
        "reason": "Replaced by graphify_agent + direct .claude/notes/ writes in v5.2",
    })

REGISTRY.write_text(json.dumps(data, indent=2), encoding="utf-8")
history_path.write_text(json.dumps(history, indent=2), encoding="utf-8")
print(f"Registry: {before} -> {after} agents (retired: {sorted(retire)})")

# --- 2. Delete wiki_updater.md + wiki_curator.md agent files -----------------
for name in retire:
    fp = ROOT / "agents" / "meta" / f"{name}.md"
    if fp.exists():
        fp.unlink()
        print(f"Deleted: {fp.relative_to(ROOT.parent)}")

# --- 3. Delete wiki_compiler.py + any wiki-related tools ---------------------
wiki_compiler = ROOT / "tools" / "wiki_compiler.py"
if wiki_compiler.exists():
    wiki_compiler.unlink()
    print(f"Deleted: {wiki_compiler.relative_to(ROOT.parent)}")

# --- 4. Delete the entire .claude/wiki/ tree ---------------------------------
wiki_dir = ROOT / "wiki"
if wiki_dir.exists():
    # Count files first for the report
    file_count = sum(1 for _ in wiki_dir.rglob("*") if _.is_file())
    shutil.rmtree(wiki_dir)
    print(f"Deleted: .claude/wiki/ tree ({file_count} files)")
else:
    print(".claude/wiki/ already gone")

# --- 5. Update security.yaml: remove wiki/** allowlist entries --------------
sec_yaml = ROOT / "policies" / "security.yaml"
text = sec_yaml.read_text(encoding="utf-8")

# Remove the wiki/** allowlist block (all 10 wiki paths)
wiki_paths_to_remove = [
    '      - ".claude/wiki/concepts/**"\n',
    '      - ".claude/wiki/strategies/**"\n',
    '      - ".claude/wiki/experience/**"\n',
    '      - ".claude/wiki/goals/**"\n',
    '      - ".claude/wiki/self/**"\n',
    '      - ".claude/wiki/patterns/**"\n',
    '      - ".claude/wiki/consensus/**"\n',
    '      - ".claude/wiki/summaries/**"\n',
    '      - ".claude/wiki/graph/**"\n',
    '      - ".claude/wiki/index.md"\n',
]
removed = 0
for p in wiki_paths_to_remove:
    if p in text:
        text = text.replace(p, "")
        removed += 1

# Also update denied list: remove wiki/raw/** (no longer exists)
text = text.replace('      - ".claude/wiki/raw/**"     # raw is immutable (append-only via repo_ingestor)\n', "")

# Remove the must_consult_before entry if it existed
sec_yaml.write_text(text, encoding="utf-8")
print(f"security.yaml: removed {removed + 1} wiki/** entries from allow/deny lists")

# --- 6. Update tool_registry.json: remove wiki_compiler entry ---------------
tr_path = ROOT / "tools" / "tool_registry.json"
tr = json.loads(tr_path.read_text(encoding="utf-8"))
before_tools = len(tr["tools"])
tr["tools"] = [t for t in tr["tools"] if t.get("name") != "wiki_compiler"]
after_tools = len(tr["tools"])
if before_tools != after_tools:
    tr_path.write_text(json.dumps(tr, indent=2), encoding="utf-8")
    print(f"tool_registry.json: {before_tools} -> {after_tools} tools (removed wiki_compiler)")

print("\nPhase 5 complete. Wiki removed from repository.")
