# Codex Global Instructions

When project-specific instructions exist, prefer them, but keep these global instructions where they don't conflict.

## Response Format

- Respond in Korean unless the user specifies another language.
- Technical terms such as code identifiers, commands, filenames, and library names may stay in their original form.
- Before editing a file, briefly explain what you're changing and why.
- When referring to code or files, use clickable absolute-path markdown links where possible.
- Propose or apply logically related changes together.
- Prefer the information the user needs to decide or act next over unnecessarily verbose explanation.

## Tool Usage

- For file-related commands, try workspace-root-relative paths first.
- Prefer `rg` or `rg --files` for searching.
- Don't read or search files that look sensitive (`.env`, private keys, credentials, tokens, kube/aws/docker config, etc.) unless they're needed.
- Don't run destructive changes the user didn't explicitly request (`rm`, force checkout/reset, etc.).
- Existing work may be mixed in, so don't revert changes you didn't make.

## Python

1. Check whether a `.venv` exists at the workspace root.
2. If it exists, run as `source .venv/bin/activate && <python_command>`.
3. If not, run the Python command directly.

## Git Commit

- Never run `git commit` on your own initiative. When asked to commit or to generate a message, **propose** the message first and commit only after the user approves. Ambiguous phrasing like "sync to git" does not mean commit.
- Always write commit messages in English, regardless of the conversation language.
- Follow conventional commit format (feat, fix, refactor, docs, test, chore, etc.).
- Keep the title concise (under 50 characters) and in imperative mood ("add", not "added"). Add a body only when the change needs explanation; mark breaking changes explicitly.
- Do NOT add AI co-author trailers (e.g., `Co-Authored-By: Claude`, `Co-Authored-By: Codex`) or generator footers (e.g., `🤖 Generated with ...`).

## Authoring Agent Instruction Files

When no project-specific instruction says otherwise, author a project's agent instruction files (AGENTS.md / CLAUDE.md) by these defaults:

- Keep AGENTS.md focused on **development-relevant** content: build/test/run commands, code conventions, architecture entry points, and the work rules an agent needs.
- Keep it **concise**. Don't duplicate detail that already lives elsewhere — **point to** the canonical document (README, design docs, specific source files) instead. AGENTS.md is an index of rules and pointers, not a copy of every document.
- Add or extend these files only when an agent genuinely needs the guidance — skip trivial or throwaway repos.
- Use the single-source pattern only when the user explicitly asks for both files, or the repo already uses it: keep the real content in AGENTS.md and make CLAUDE.md a single-line `@AGENTS.md` import (Codex reads AGENTS.md natively; Claude Code reads CLAUDE.md → import). Otherwise author only the file you were asked for — if the user asks for a CLAUDE.md only, write just that, and don't restructure an existing instruction file uninvited.
- These are defaults; an explicit user instruction takes precedence.
