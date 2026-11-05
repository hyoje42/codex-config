---
name: verify-computation
description: "Verify that computed results (aggregates, scores, geometry, schedules, routes, placements, optimizer output) are correct using references independent of the implementation: hand-computed cases, brute force on small inputs, metamorphic relations, and an independent checker that recomputes metrics and constraint violations from raw inputs. Use when tests pass but the numbers are hard to trust, when a checker may share the generator's mistakes, when building an evaluator or constraint checker, or when assigning a verification agent. Not for general code review or performance work."
---

# Verify Computation

Check whether the computation and its tests share the same wrong assumption. If the request is a review, give reproductions and a judgment; if it includes fixing, fix the confirmed defects.

Ordinary testing practice (test through public interfaces, take expected values from the spec rather than from the code) is assumed. This skill adds how to obtain references that can disagree with the code, how to check candidate outputs independently, and how to show which constraints are actually covered.

## 1. Fix the claims

Extract from the spec and the public inputs and outputs what must be guaranteed. Make explicit, where relevant: units, denominators, what is aggregated, duplicate handling, when rounding happens, and boundary inclusivity. If expected behavior is ambiguous, do not take the implementation as the answer; list the assumption and its alternative.

Correctness, constraint satisfaction, and optimality are different claims. Finding a feasible result does not show optimality, and a failed search does not prove that no valid result exists.

## 2. Choose independent references

Pick what fits; not every method is needed.

| Situation | Method | Limit |
| --- | --- | --- |
| The answer for a small input can be computed directly | Fix hand-computed inputs and expected values, with the derivation (inputs, rule, result, spec section) | Says nothing direct about large inputs |
| Quality of an optimizer or approximation | Compare with brute force or a deliberately simple separate implementation on small instances | Small-instance optimality is not large-scale optimality |
| The exact answer is hard, but a relation must hold | Check the relation across input transformations | A result can satisfy the relation and still be wrong |

Use only relations the spec guarantees, such as a sum unchanged by reordering input, or distances unchanged when all coordinates shift together. If ties or order dependence exist, do not require identical full outputs.

Confirm that reference code does not call the implementation's helpers. An independent implementation can still copy the same formula or mistake, so check at least one case against a value a person can explain.

## 3. Independent checker (for candidate outputs)

When the product emits candidates (plans, schedules, placements, assignments), build or audit a checker that reads raw inputs plus a candidate in the output format and recomputes everything.

- Contract: how it is invoked; inputs (data, configuration or variant, candidate); outputs (valid / violates / invalid input, metrics, violations with stable codes and locations such as IDs, coordinates, or times, rejected candidate items with reasons, claimed-versus-recomputed mismatches).
- Use the candidate's own metrics and status only to flag mismatches. Never adjust the checker so that a particular output passes.
- If the input has variants (configurations, change sets), apply them to copies of the input, and reject unknown ones explicitly instead of silently checking against the default input.
- Keep the verdict separate from product policy. Whether an invalid result may still be saved, shown, or exported (for example for analysis) is decided by the product's requirements; implement what they say, and never present an invalid result as valid.

Keep a coverage table, `constraint | check (file:line) | test | status`. An empty cell is a gap to fix or report.

## 4. Check that plausible wrong answers are caught

- Start from a valid candidate and change one condition at a time: just before, at, and just after each boundary that matters; duplicates and omissions; values before and after rounding. Do not add unrelated exception lists in bulk.
- Tamper with the candidate's reported metrics or status and confirm the checker recomputes from the raw input. Break one constraint and confirm the matching violation code appears.
- In a throwaway copy or worktree, break one rule in the product code (remove a margin, drop a filter, flip a boundary) and confirm a test fails for that reason, not because of an import or syntax error. Discard the copy.
- Exercise the real API, CLI, or serialization path for the cases that matter, not only internal functions.
- Ask the user to confirm one or two expected values by hand: two AIs can share the same misreading.

## 5. Delegating to a verification agent

Only when the user asks for one.

- Confirm the agent actually started before saying so. Use the environment's subagent mechanism; if per-agent model or effort settings exist, request what the user named. If subagents are unavailable, print the brief for the user to paste into a second session.
- Ownership: the verifier edits only the test or verification folder and its log. It reports product bugs with `file:line`, a reproduction, and the expected value with its source. Changes to dependencies or the test runner go through the main session.
- The brief is self-contained: spec path, owned paths, sections 1-4 of this skill, and the report format below.
- The default test command must pass without special flags. Mark planned-but-missing features as strict expected failures with a reason, and remove the marker when the feature lands. Fixtures state which data mode they use, so a change of the product's default data cannot silently break them.

## 6. Report

Give the claims checked, where each reference came from, inputs with expected and actual values, and the exact commands with results. Leave each defect as a minimal reproduction; after a fix, rerun it and the related regressions.

Report correctness outside the checked range as unverified. Do not declare mathematical correctness from a test count or from two implementations agreeing.
