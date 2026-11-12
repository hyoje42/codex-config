# Decision Packages

Every stop shows the user one package in their language. A package reports what agents already verified and asks only for decisions agents cannot make.

## How to Present a Stop

Make the decision understandable without opening the stage files.

- **Write out what is being decided.** Print the spec checklist, the findings, or the proposed changes item by item in the package. A stage-file path or an ID range such as `S1-S6` never stands in for the content; paths are for detail beyond it. Keep the package short by leaving out how you got there, not what the user is approving.
- **Print the package before asking.** When the question tool's contract permits the question, print the package as message text in the same turn before calling it. The dialog only collects the answer. Otherwise put the full package followed by the question together in the final response, so it remains self-contained even when earlier commentary is collapsed.
- **Record the pending decision.** Before asking, record in `state.md` which stop and decisions the loop is waiting at. After an explicit reply, record the decision and clear only the resolved pending items.
- **Make each question readable on its own.** A dialog can cover the text above it, so describe the goal and the points needing the user's judgment in a sentence or two instead of naming an ID range.

## Shared Shape

1. **First line:** what is being decided and the orchestrator's recommendation.
2. **What is being decided:** the content listed for that package below, written out.
3. **Verified by agents:** what was checked, by which judge (name the model when known), and the result. Include known weaknesses such as "same-model reviewer" or "no integrity checks".
4. **Needs your decision:** only items agents could not settle, each with options and a recommended one.
5. **Files:** paths to the stage files for detail.
6. **Ask** after the package text using the mechanism in SKILL.md: at most 3 questions per batch, recommended option first. Wait for an explicit reply to each required decision.

## Intent Stop ([1])

Ask only outcome-changing unknowns that the repo and context file could not answer. For each, state what was already checked and why it did not settle the question, in the package and briefly in the question or its option descriptions.

## Spec Package ([2])

- Goal restated in one sentence.
- Spec checklist, every item written out: its ID, the requirement in one line, and how it is checked. Keep the facts, hypotheses, decisions, and unknowns separate, and write out each decision and unknown the same way.
- Slots: 5-a gates, 5-b judges, done definition, K, and risk tier, each marked as from the context file or a default.
- Mode the run will use. If auto mode was requested and refused, name the failed precondition.
- Resolved roster: runner and model per role, with any model that is assumed rather than known marked as such. Say that it can be changed here in plain words, and show how you read any roster request made in the invocation.
- Slice plan: slices, parallel groups, dependencies.
- Plan-review result: verdict per round, what it caught and fixed, findings applied without re-review after a failed last round, and any open disagreement.
- A context-file draft, if [0] created one: its rules and unverified assumptions in a few lines, plus its path.
- Options: approve, change (say what), stop.

## Final Package ([5-b], in mode)

- Verdict of the judges and the recommendation.
- 5-a results: commands and exit codes.
- 5-b results: deterministic judges, then `verifier` findings with severity.
- Every finding fixed automatically, with the spec item it cited and how it was fixed.
- Spec gaps, spec items the reviewer could not check, and residual risks. Each spec gap needs a decision: add it to the spec, or accept the work as is.
- Reviewer notes, copied as written.
- Integrity-check results: the change list, and any violation that was repaired.
- Proposed changes to `.loop/context.md`, each one written out as it stands in `6-context-proposal.md`.
- Options: accept, send back to the spec (say what is wrong), stop. Accepting does not approve a commit; propose the commit separately.
- A second question in the same decision package: apply the context proposal, apply it with changes, or leave the context file as it is.

## Escalation

- What stopped the loop: the limit hit, the out-of-scope action, the failed integrity check, the spec gap, or the unanswered unknown.
- What was tried, and the evidence (attempt count, gate output excerpt, finding).
- Options to continue, with a recommendation.

## Delivered Report (auto mode)

The same content as the final package, written to `6-report.md` and summarized at the end of the run. The user reviews it after the fact and decides on `6-context-proposal.md` and the commit.
