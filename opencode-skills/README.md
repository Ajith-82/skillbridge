# OpenCode Skills

This directory stores repo-managed OpenCode skills for local development alongside `skillbridge`.

## Sync model

- The canonical editable copies live in this repo.
- OpenCode loads them through symlinks under `/home/cloud/.config/opencode/skills/`.
- For example, `cadence-skill-programmer` is linked from `/home/cloud/.config/opencode/skills/cadence-skill-programmer` to `opencode-skills/cadence-skill-programmer`.

## Current skills

- `cadence-skill-programmer` - Cadence Virtuoso SKILL coding skill with a prebuilt local documentation index and skillbridge verification helpers.

## Maintenance

- Edit skill files here in the repo, not in `~/.config/opencode/skills/`.
- Rebuild generated indexes only when the underlying documentation install changes.
- Package a skill from the repo copy so the archive matches what is version-controlled.
