# Codex Runners

Read this before resolving the roster. Treat the live tool schema and installed `codex --help` / `codex exec --help` as the capability contract. Do not copy Claude tool names, model aliases, permission allowlists, or JSON events into Codex calls.

## agent (default)

Use the native subagent tools exposed by the host. This skill explicitly requests delegation for implementation and independent checks.

- Start every worker with a self-contained prompt from [prompts.md](prompts.md). For judges, create a new agent on every round; never reuse an implementer thread.
- On hosts exposing `collaboration.spawn_agent`, pass `task_name`, `message`, and `fork_turns="none"`. Pass `model` and `reasoning_effort` only when explicitly configured and authorized. This interface has no `agent_type` parameter.
- On hosts exposing `spawn_agent` with `fork_context`, use `fork_context=false` and its actual prompt/type parameters. Pass `agent_type` or model/effort only if that schema supports them. A role named "reviewer" does not by itself prove a different model or a read-only sandbox.
- If the host cannot guarantee a fresh conversation, use an available `codex-cli` runner and disclose the change before the spec is approved. If neither can do it, report the blocker. Never silently downgrade to inherited-history review.
- Record returned agent IDs. Use completion notifications or the host's wait tool; follow its timeout limits and keep the user informed during long runs. Use follow-up tools only for an implementer's corrective work, never to turn that worker into a judge.
- Respect the available concurrency slots. Close completed agents when the host supports it; otherwise reuse idle implementers for their own fixes or run queued work sequentially. Do not change host concurrency settings.

Native agents inherit host permissions. A prompt requesting read-only work is an instruction, not an enforced sandbox. Run the before/after integrity checks even when an agent reports that it changed nothing. Shared working directories also mean read-only reviewers must run after writers and gates finish.

## codex-cli

Use a fresh `codex exec` process when selected in the roster or when the host cannot provide a fresh native agent. Check the installed CLI flags first. Do not use `exec resume` or `exec fork` for judges.

Prepare prompts and output directories before the per-run snapshot. Use a unique `<run-id>` for each attempt so earlier evidence is preserved. Substitute real, shell-quoted absolute paths for `<repo>`, `<task>`, and `<run-id>` below; these are templates, not literal commands.

Reviewer / checklist gate checker:

```bash
codex -a never exec --ephemeral --sandbox read-only --json \
  -C '<repo>' -o '<task>/logs/<run-id>.md' - \
  < '<task>/prompts/<run-id>.md' \
  > '<task>/logs/<run-id>.jsonl' 2> '<task>/logs/<run-id>.err'
```

Implementer:

```bash
codex -a never exec --ephemeral --sandbox workspace-write --json \
  -C '<repo>' -o '<task>/logs/<run-id>.md' - \
  < '<task>/prompts/<run-id>.md' \
  > '<task>/logs/<run-id>.jsonl' 2> '<task>/logs/<run-id>.err'
```

- Add `--model <model>` and `-c 'model_reasoning_effort="<effort>"'` only for authorized roster values; quote them correctly. Leave both out to use CLI defaults. `agent_type` is native-only; do not silently ignore a requested value on CLI.
- `-a never` is a global option before `exec`; a denied action fails rather than waiting for unattended approval. Preserve the host's stricter requirements. A shell tool permission failure is not a reason to relaunch outside its sandbox.
- `read-only` restricts model-executed shell writes. The parent shell and CLI still write the selected logs. `workspace-write` does not enforce a slice's allowed-file list; snapshots remain necessary.
- Shell sandbox settings do not impose read-only permissions on MCP servers, apps, or other connected tools. Restrict these workers to repository evidence and prohibit external mutations in their prompts; do not claim complete tool isolation. If the task requires enforceable restrictions beyond what the host provides, report that capability gap.
- Gate commands may create caches or build outputs. Read-only CLI judges use the recorded results; they report unavailable checks rather than weakening the sandbox.
- Do not add bypass flags, writable directories, change global configuration, or discard user/project rules to make a run succeed. A missing executable, unsupported flag, sign-in problem, or denied permission is a runner failure. Resolve within existing authorization, retry once, then escalate if still blocked.
- Outside Git, add `--skip-git-repo-check` only for an approved in-mode task already declaring the integrity limitation.

Launch through the shell execution tool, using its background/session mechanism when available. For `exec_command`, keep the returned session ID and use `write_stdin` to collect completion. Other hosts may provide notifications instead. Do not confuse a yielded tool session with a finished worker.

### Reading a run

Read the process exit code, final message file, and JSONL events. With `jq` installed:

```bash
jq -c 'select(.type == "turn.completed" or .type == "turn.failed" or .type == "error")' '<task>/logs/<run-id>.jsonl'
jq -r 'select(.type == "item.completed" and .item.type == "agent_message") | .item.text' '<task>/logs/<run-id>.jsonl'
```

A successful process is not a passing gate or verdict. Require a completed turn and a substantive report; inspect failed command items and any reported denials. A nonzero exit, failed turn, missing completion, or missing report is a runner failure under stage [4], not a consumed 5-a attempt. Earlier recoverable error events need inspection, not automatic acceptance or rejection. Without `jq`, read the JSONL and final message using available file tools; only the optional tmux filter requires `jq`.

Codex JSONL does not guarantee model identity in `thread.started`. Record effective identity only when runtime metadata or established configuration supplies it; keep requested identities separate from verified identities. Never read authentication files to establish a model. Unknown defaults cannot satisfy on mode's different-model requirement.

## view=tmux (optional)

Only use this for a CLI role when `TMUX` is set and both `tmux` and `jq` are installed. Otherwise record that the optional view is unavailable and continue the worker. Native agents use the host's activity view.

After starting the worker and creating its log, open a read-only pane with real, correctly quoted paths:

```bash
tmux split-window -d -h -c '<repo>' -P -F '#{pane_id}' \
  "tail -n +1 -f '<task>/logs/<run-id>.jsonl' | jq -r --unbuffered -f '<skill-dir>/scripts/pane-filter.jq'"
```

Record the pane ID, then close only that pane with `tmux kill-pane -t <pane-id>` when its run ends. The pane is a display, not a control channel; never use `send-keys` to drive the agent.

## Sources and compatibility

Converted against local `codex-cli 0.167.0` help and official [subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [non-interactive documentation](https://developers.openai.com/codex/noninteractive). Installed tool schemas and CLI flags take precedence over examples. No model ID is pinned by this skill.
