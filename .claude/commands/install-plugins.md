# /install-plugins

Install (or list) the plugins this repo uses, per `.claude/plugins-manifest.json`.

Per v5.3 Council decision, plugins are adopted **by reference, not by copy**.
When you clone this repo, run this command to install all recommended plugins into
your local `~/.claude/` — upstream versions, fresh from each plugin's marketplace.

## Usage

```bash
py -3 .claude/tools/install_plugins.py              # print install commands for 'core' plugins
py -3 .claude/tools/install_plugins.py --all        # core + optional
py -3 .claude/tools/install_plugins.py --lsp python # add the Python LSP plugin
py -3 .claude/tools/install_plugins.py --exec       # run the commands via `claude` CLI if on PATH
py -3 .claude/tools/install_plugins.py --list       # show the full manifest (every plugin + reason)
```

## What gets installed (core)

8 plugins route the system's everyday work:

- `commit-commands` — /commit, /commit-push-pr, /clean_gone
- `security-guidance` — security_reminder_hook source
- `claude-md-management` — constitution maintenance skill
- `voltagent-lang` (30 language experts)
- `voltagent-dev-exp` (15 dev-experience experts)
- `voltagent-qa-sec` (16 QA + security experts)
- `voltagent-research` (9 research experts)
- `voltagent-data-ai` (14 data + ML experts)

Optional and language-specific LSPs are listed separately — install on demand.

## Why not vendor-copy the plugins?

Same reason the Council rejected voltagent vendoring in v5.3 (see
`.claude/notes/consensus/v5.3-specialist-integration.md`):

- Fossilises versions → no upstream security/bug fixes.
- Each plugin has its own LICENSE → redistributing bundles inside our repo creates license-management burden for every downstream user.
- Plugins are designed to be installed via `/plugin install` by Claude Code — that's the intended path.

**Net effect** for the end user is identical: they clone the repo, run this
command once, and all the plugins are live in their Claude Code install.

## Managing the manifest

Edit `.claude/plugins-manifest.json`:

- **Add a plugin to `core`**: if this repo actively relies on it. Document `why`.
- **Move to `optional`**: if it's nice-to-have for specific tasks.
- **Add to `skip`**: if someone might assume it applies, but we don't use it. Document `why_skip`.

Commit any manifest changes. The manifest IS the project's statement of "what external tooling this repo expects."
