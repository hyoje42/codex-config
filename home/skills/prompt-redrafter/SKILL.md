---
name: prompt-redrafter
description: rewrite rough prompts into clearer, more effective prompts that follow practical prompt engineering best practices. use when a user gives a messy draft prompt, notes, or a vague task and wants it improved, structured, tightened, or made more reliable for chatgpt or another llm. default to producing an immediate improved prompt first, then offer a small number of optional follow-up questions only when they would materially improve the result. useful for everyday business prompting, document work, research tasks, connector-based search prompts, and high-stakes prompts that need better scope, structure, and accuracy guardrails.
---

# Prompt Redrafter

## Overview

Turn rough prompts, notes, or loosely described tasks into cleaner prompts that are easier for ChatGPT to execute well.

Bias toward giving the user a strong first rewrite immediately. Preserve the user's actual intent, but normalize the prompt so that the task, context, and success criteria are more explicit.

## Core workflow

1. Read the user's rough prompt or notes and infer the underlying job to be done.
2. Rewrite immediately instead of interrogating first.
3. Tighten scope so the prompt targets one deliverable unless the user explicitly wants a multi-part workflow.
4. Add structure with markdown headers when it improves clarity.
5. Add only the most useful missing details that are strongly implied by the user's request; do not invent factual content.
6. If the task is factual, risky, or decision-relevant, add lightweight accuracy guardrails.
7. After the rewritten prompt, optionally add a very short "Possible improvements" section with 1-3 follow-up questions only if answers would materially improve the prompt.

## Rewrite rules

### 1. Preserve intent, upgrade clarity

- Keep the user's real goal intact.
- Improve wording, specificity, and ordering.
- Prefer clarity over cleverness.
- Remove fluff, repetition, and contradictory instructions.

### 2. Scope to one deliverable when possible

- If the prompt is overloaded, narrow it to the clearest immediate output.
- Break broad asks into phases only when necessary.
- If keeping multiple outputs is important, sequence them clearly.

### 3. Use markdown structure flexibly

Use headers when they make the task easier to understand. Do not force the same template every time.

Common useful section patterns:
- `# Context`
- `# Task`
- `# Instructions`
- `# Audience`
- `# Output format`
- `# Constraints`
- `# Sources to use`
- `# Evaluation criteria`

For simple asks, a short single-block prompt may be better than a fully sectioned prompt.

### 4. Make "good" explicit

When useful, specify:
- audience
- tone
- length
- format
- required coverage
- exclusions
- acceptance criteria

Only include the constraints that meaningfully improve the output.

### 5. Add guardrails when the task needs them

For factual, analytical, or high-stakes tasks, consider adding brief instructions such as:
- do not invent facts
- cite or quote source material when available
- label uncertainty clearly
- separate facts from assumptions
- list open questions or missing information
- check completeness against required criteria before finalizing

Do not overload simple creative or low-stakes prompts with unnecessary guardrails.

## Decision guide

### If the input is extremely rough

Infer the most likely task and produce a best-effort rewrite.

Examples:
- fragmented notes
- shorthand bullets
- vague request with a target audience implied
- a user saying "make this a better prompt"

### If the task is simple

Keep the rewrite compact. Do not expand a short prompt into an over-engineered template.

### If the task is complex

Use sections and explicit output requirements.

### If the task relies on source material the user has not provided

Do not pretend prompting alone solves the problem. You may mention what additional source material would improve the result.

## Output style

Default output:
1. Title: `Improved prompt`
2. The rewritten prompt in a markdown code block
3. Optional: `Possible improvements` with 1-3 concise questions or suggestions

Keep commentary minimal. The primary value is the rewritten prompt itself.

## Quality bar for the rewritten prompt

A strong rewrite should:
- be easy for another person to understand without extra explanation
- make the requested output shape clear
- reduce ambiguity that would predictably hurt quality
- preserve the user's intent and useful wording where possible
- avoid adding unsupported factual assumptions
