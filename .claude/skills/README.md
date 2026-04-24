# .claude/skills/ - Skills Directory (v5.4 scaffold)

This dir complements .claude/commands/. Skills bundle SKILL.md + supporting
files (checklists, schemas, templates). Commands are single-file and still
fully supported. Migrate a command to a skill only when bundling is useful.

## Layout

    .claude/skills/
      <name>/
        SKILL.md            # required; YAML frontmatter + body
        <supporting>.md     # optional bundled reference

## Frontmatter fields

- name (required)
- description (required; first 140 chars shown in / menu)
- argument-hint: <text>         # e.g. "<issue-number>"
- disable-model-invocation: true   # skill invocable by user only, not Claude
- user-invocable: false            # hides from / menu; Claude-only
- context: fork                   # run in isolated context

## $ARGUMENTS variable

Skill body can reference $ARGUMENTS (full input) or $0, $1 (positional).

## When to prefer a skill over a command

- Bundled reference docs (checklists, API schemas, response templates)
- Multi-step workflow with file artifacts (plans, reports)
- Side-effecting actions that should be user-invocable only (deploy, publish)

Otherwise keep it a single-file command in .claude/commands/.
