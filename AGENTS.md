# Codex Config Repo — Work Guide

A submodule of `dev-ai-tools`. For the overview (structure, scripts, machine-specific mechanism, etc.), see [README.md](./README.md). This document holds only the rules an agent must follow when editing/managing this repo.

Path map: only `home/` syncs to `~/.codex/` · `local/` holds machine-specific templates (`*.example`) · the real machine values live in `~/.codex/config.toml` (which the repo does not read).

## Work rules

- **Sync gate**: applying to `~/.codex/` (whether via `codex-sync-to-home` or a manual copy) happens **only when the user explicitly says so**. Normally just check the diff with `codex-diff-with-home` and share it.
- **Sync-area boundary**: do not move files outside `home/` into the sync target, or vice versa.
- **Machine-specific values**: commit only the `*.example` in `local/`. Do not commit the real values (`~/.codex/config.toml`, etc.). config.toml is **seed-if-absent** (seeded only when missing, preserved when present), not a merge.
- **Preserve approval rules**: `~/.codex/rules/default.rules` is Codex's approval-rules file, so this repo does not overwrite it.
- **Commit order**: commit in the submodule first → then commit the pointer bump in the parent.
- **Do not port mechanisms**: do not move claude-config's settings-merge approach here (i.e., don't move seed-if-absent the other way either).
- **Authoring/porting skills**: for the format and the Claude→Codex conversion rules, see [skill-authoring.md](./skill-authoring.md).
