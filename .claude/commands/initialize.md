---
description: Initialize the Meta-Orchestration Agent System — scan repo, detect stack, generate project_overview.md, verify registry, print banner.
argument-hint: (no arguments)
---

# /initialize — Bootstrap the Agentic System

You are about to run the one-time initialization routine for this repository's Meta-Orchestration Agent System.

Follow these steps **in order**. Do not skip any.

---

## Step 1 — Read the constitution

Read `.claude/CLAUDE.md` and `.claude/runtime.md`. You are now bound by them for the duration of this session.

## Step 2 — Scan the repository

Using Glob and Read (no Write yet):

- List the top two levels of the working directory (max depth 2).
- Identify the tech stack via these heuristics (first match wins; multiple may apply):

  | Signal file                   | Stack                  |
  | ----------------------------- | ---------------------- |
  | `package.json`                | Node / JavaScript      |
  | `pnpm-lock.yaml`              | Node (pnpm)            |
  | `yarn.lock`                   | Node (yarn)            |
  | `tsconfig.json`               | TypeScript             |
  | `pyproject.toml`, `setup.py`, `requirements.txt` | Python |
  | `Cargo.toml`                  | Rust                   |
  | `go.mod`                      | Go                     |
  | `pom.xml`, `build.gradle`     | JVM (Java/Kotlin)      |
  | `Gemfile`                     | Ruby                   |
  | `composer.json`               | PHP                    |
  | `*.csproj`, `*.sln`           | .NET                   |
  | `Dockerfile`                  | (also capture)         |
  | `.github/workflows/*.yml`     | CI: GitHub Actions     |

- Count source files per language (rough, via Glob).
- Note any existing `.claude/` entries beyond the seed files.

## Step 3 — Generate `project_overview.md`

Write a file at the **repository root** (not inside `.claude/`) called `project_overview.md`. Format:

```markdown
# Project Overview

Generated: <ISO-8601 timestamp>

## Stack
- Primary: <language>
- Secondary: <languages>
- Build: <npm / uv / cargo / ... >
- CI: <GitHub Actions / none>

## Structure
- Top-level directories: <list>
- Entry points detected: <list>

## Agentic runtime
- Orchestrator, Factory, Evaluator, Wiki Updater, Wiki Curator are registered.
- Wiki is empty (fresh boot) — concepts will grow with use.
- See `.claude/CLAUDE.md` for the constitution, `.claude/runtime.md` for the loop.

## Next steps for the user
- Invoke the orchestrator with a real task to populate the wiki.
- Run `python .claude/tools/repo_ingestor.py --url <repo>` to seed knowledge from external sources.
```

If `project_overview.md` already exists, **do not overwrite**. Read it, diff the stack section, and append a `## Re-initialization notes (<timestamp>)` section instead.

## Step 4 — Verify the registry

Run:

```bash
python .claude/tools/agent_validator.py --self-test
```

- Expected: exit 0, five agents reported OK.
- If it fails: **stop**. Do not print the banner. Report the error to the user verbatim.

## Step 5 — Verify the directory structure

Confirm these directories exist (create empty if missing — one of the rare times you may write outside the agent pipeline, because initialization is setup, not task execution):

```
.claude/wiki/raw/github/
.claude/wiki/raw/papers/
.claude/wiki/raw/docs/
.claude/wiki/concepts/
.claude/wiki/summaries/
```

## Step 6 — Log the initialization

Append one entry to `.claude/memory/logs.json`:

```json
{
  "task_id": "init-<short-uuid>",
  "timestamp": "<ISO-8601>",
  "outcome": "initialized",
  "agents_used": [],
  "wiki_updates": [],
  "notes": "system initialized via /initialize"
}
```

## Step 7 — Print the success banner

Only after steps 1–6 all succeed, print **exactly**:

```
🚀 Agentic System Initialized
```

No additional commentary. The user will follow up.

---

## Failure handling

If any step fails:

1. Do **not** print the success banner.
2. Append a log entry with `outcome: "init_failed"` and the failing step number.
3. Report the specific failure to the user and stop.
