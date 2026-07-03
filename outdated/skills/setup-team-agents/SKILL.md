---
name: setup-team-agents
description: "Design and, when the user explicitly asks for agent delegation, spawn a small Codex sub-agent team for complex work that benefits from multiple independent perspectives. Trigger on '/setup-team-agents <description>', 'set up team agents', 'create agent team', 'build a swarm', or similar explicit requests. Do not use for ordinary single-agent work."
compatibility: "Codex-compatible adaptation. Codex supports spawn_agent/send_input/wait_agent, but not Claude TeamCreate/TaskCreate shared task infrastructure."
---

# Setup Team Agents

## Purpose

Create a Codex-compatible collaboration setup for complex work. This is not a
byte-for-byte equivalent of Claude Team Agents: Codex has sub-agents, but no
shared TeamCreate/TaskCreate board or built-in inter-agent messaging fabric.

## Hard Constraints

- Only spawn agents when the user explicitly asks for sub-agents, delegation,
  parallel agent work, or invokes this skill.
- Do not claim a Claude-style team workspace exists.
- Use `spawn_agent` only for concrete, bounded tasks that can run in parallel.
- Tell worker agents they are not alone in the codebase and must not revert
  edits made by others.
- For code-writing agents, assign disjoint ownership of files/modules.
- Keep the main Codex agent responsible for orchestration, integration, and the
  final answer.
- Write team design documents, agent prompts, and generated markdown artifacts
  in the user's explicitly requested language; if no language is specified,
  write them in the user's preferred language.

## Workflow

1. **Analyze the task from the user request**
   - Core objective and scope
   - Areas where independent perspectives help
   - Risks, trade-offs, and likely integration points

2. **Create a local team workspace**
   - Use KST date: `TZ='Asia/Seoul' date +"%y%m%d"`
   - Create `.teams/YYMMDD-<task-slug>/`
   - Write `.teams/YYMMDD-<task-slug>/team-design.md`

3. **Design 2-5 roles**
   - Prefer distinct perspectives over sequential phases.
   - Examples: explorer, implementation worker, test/verification worker,
     critic/reviewer, synthesizer.
   - Use `explorer` for read-only codebase questions.
   - Use `worker` for bounded implementation with clear file ownership.

4. **Spawn only useful parallel agents**
   - Spawn agents whose work can proceed without blocking the immediate local
     next step.
   - Do not delegate urgent blocking work.
   - Do not duplicate the same investigation across agents.

5. **Continue local work while agents run**
   - Do meaningful non-overlapping work locally.
   - Wait only when their result is needed for the next step.

6. **Integrate results**
   - Review returned findings or patches.
   - Resolve conflicts and verify behavior locally.
   - Summarize what each agent contributed in the final answer when relevant.

## Team Design Template

Save this as `.teams/YYMMDD-<task-slug>/team-design.md`:

```markdown
# Team Design: {task summary}

> **Task**: {original user request}
> **Date**: {YYYY-MM-DD}
> **Compatibility**: Codex sub-agent workflow, not Claude TeamCreate/TaskCreate.

## Roles

| Agent | Type | Responsibility | File Ownership / Scope |
|-------|------|----------------|------------------------|
| {name} | explorer/worker/default | {bounded task} | {paths or read-only scope} |

## Parallel Work Plan

- Main agent: {local critical-path work}
- {agent}: {parallel sidecar work}
- {agent}: {parallel sidecar work}

## Integration Plan

- {how results will be reviewed}
- {tests or checks to run}
- {conflict handling}
```

## Spawn Prompt Pattern

For an explorer:

```text
You are part of a Codex sub-agent team. Your task is read-only:
{specific question}

Scope: {paths/modules}
Return concise findings with file paths and line numbers. Do not edit files.
```

For a worker:

```text
You are part of a Codex sub-agent team. You are not alone in the codebase:
do not revert edits made by others, and adapt to concurrent changes.

Ownership: {specific files/modules}
Task: {specific implementation}

Edit files directly in your forked workspace. In your final answer, list the
files changed and the checks you ran.
```

## Reporting

After setup or spawn, report:

```markdown
**Team Ready**

Workspace: `.teams/YYMMDD-<task-slug>/`

Agents:
- {name}: {role and scope}

Main-agent work:
- {what Codex will handle locally}

Compatibility note:
- Codex does not provide Claude TeamCreate/TaskCreate; this uses Codex
  sub-agents with local orchestration.
```
