---
name: explain-back
description: "Help the user understand an implementation well enough to explain and maintain it without reading the code: report the current state from evidence, walk through the key flows (trigger, functions, data, storage, output, failure points, design reasons, limits), and confirm understanding by having the user explain parts back and comparing that with the code. Use when the user asks what was built, how something works, or what a value means, or wants to be sure they understand code (often AI-written) before relying on it, reviewing it, handing it off, presenting it, or maintaining it."
---

# Explain Back

## Purpose

Code written quickly, especially by an agent, can grow faster than the person responsible for it understands it. They then mistake sample output for real results, cannot say where data goes or how failures surface, and cannot judge the next change. This skill closes that gap with facts from the current code, not from memory of earlier conversation.

## Boundaries

- Read-only. Do not edit files or run commands with side effects unless the user asks. Reading code, `git log`, `git status`, and `git diff` are fine.
- Do not rerun tests just to answer. Cite the latest known run with its command and code state, and say whether the code has changed since. Run tests only when the user asks for verification.
- Separate what the code shows, what a run showed, and your own inference. Written, run, and passed are different claims.
- Explain only what changes the user's understanding; no tutorials and no restating of the whole design.

## Status

Use for "what is there now?" questions.

1. Check `git log --oneline -5`, `git status --short`, and which data or configuration the program currently uses (sample, real, or another variant), including whether stale sample output is still visible.
2. Reply briefly. The first sentence states the current state in one line, for example "Import and validation work on the real files; the monthly report still reads the sample data."
3. Then: what runs and on which data (command or URL), progress against the requirements with evidence, the latest change in one or two lines, the meaning of any value or label the user will see, and the next step with how to tell it is done.

## Walkthrough

Use when the user wants to understand how it works. Pick the two or three flows that matter most (the main user action, the main computation, the main failure path), or the flows the user names. For each flow:

1. **Diagram**: an ASCII diagram from trigger to visible result.
2. **Steps**: trigger → entry point → each function that changes the data (`file:function`) → storage → output. Say what the data looks like at each step when it changes shape.
3. **State**: what is stored where, and what changes on rerun, restart, or new input.
4. **Failure**: where it can fail, what happens to existing results, and who sees what.
5. **Reason**: why this design over the obvious alternative, and what it does not guarantee.
6. **How to say it**: three to five plain sentences the user could use to explain the flow without the code.

End with the terms the user must use precisely, such as time order or units, and the files worth reading first.

## Explain-Back Check

Use when the user wants to confirm their understanding.

1. Study the relevant code first, and note the facts an accurate explanation must contain, without printing them.
2. Ask the user to explain one flow, or to answer one concrete situation ("an input row has an unknown ID; what happens from upload to report?"). Ask one at a time and cover reason, flow, state, failure, and how correctness is known.
3. After each answer, compare it with the code: what is right, what is missing, what is wrong, each with `file:function`.
4. Follow the user's preferences for the number of questions, hints, and when to give feedback. Without preferences, ask about five, give no hints before an answer, and give feedback after each one.
5. Finish with the weakest spots and where to reread them (`file:line`).
