# Codex Config Repo — Work Guide

A submodule of `dev-ai-tools`. For the overview (structure, scripts, machine-specific mechanism, etc.), see [README.md](./README.md). This document holds only the rules an agent must follow when editing/managing this repo.

Path map: `home/skills/` syncs to `~/.agents/skills/` · the rest of `home/` syncs to `~/.codex/` · `home/config.toml` is merged into `~/.codex/config.toml` instead of being copied verbatim · `local/` holds machine-specific templates (`*.example`) and ignored real overrides.

## Work rules

- **Sync gate**: applying to `~/.codex/` or `~/.agents/skills/` (whether via `codex-sync-to-home` or a manual copy) happens **only when the user explicitly says so**. Normally just check the diff with `codex-diff-with-home` and share it.
- **Sync-area boundary**: do not move files outside `home/` into the sync target, or vice versa.
- **Shared skill target**: `~/.agents/skills/` may contain skills managed elsewhere. Sync and orphan cleanup must touch only skill names present in this repo; never treat the whole directory as exclusively managed.
- **Sync-script validation**: after changing Codex skill path or sync behavior, run `for script in codex-diff-with-home codex-sync-to-home tests/sync-skill-paths.sh; do bash -n "$script"; done` and `./tests/sync-skill-paths.sh`.
- **config.toml merge**: `home/config.toml` is the shared baseline. Optional real machine values go in ignored `local/config.override.toml` (template: `local/config.override.toml.example`). Sync merges current `~/.codex/config.toml` + baseline + local override; later layers replace matching keys and add missing keys while preserving unrelated current keys.
- **TOML scope**: when editing `home/config.toml` or `local/config.override.toml.example`, keep top-level keys before the first table header, and keep table-scoped keys under their matching header (for example, `[features]`). Do not rewrite a table-scoped key as a dotted key when that table is declared elsewhere; TOML can treat that as a duplicate declaration or a different nested key.
- **Preserve approval rules**: `~/.codex/rules/default.rules` is Codex's approval-rules file, so this repo does not overwrite it.
- **Commit order**: commit in the submodule first → then commit the pointer bump in the parent.
- **Do not port mechanisms blindly**: Claude uses JSON settings merge; Codex uses TOML config merge plus separate runtime wrapper handling. Convert semantics intentionally when moving rules between tools.
- **Authoring/porting skills**: for the format and the Claude→Codex conversion rules, see [skill-authoring.md](./skill-authoring.md).
- **Explicit-invocation-only skills**: add `agents/openai.yaml` with `policy.allow_implicit_invocation: false`. Keep `SKILL.md` frontmatter limited to `name` and `description`; do not rely on description wording to prevent automatic invocation.
