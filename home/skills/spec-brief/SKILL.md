---
name: spec-brief
description: "Turn a spec (requirements doc, README, PRD, ticket, design note) and any supplied data into a short, decision-ready brief: what is being built, an ASCII component diagram, a requirement table with source anchors and observable done criteria, rules and constraints with exact boundaries, data problems found by a read-only audit, and open interpretations with recommended defaults. Use at the start of spec-driven work, or whenever the user is unsure what the spec actually asks."
---

# Spec Brief

## Purpose

Much rework in spec-driven work comes from misreading the spec: which parts exist and what each is responsible for, which conditions are mandatory, what a term or value means, and which input rows will break assumptions. Answer those once, from the source, before building.

## Boundaries

- The spec and the supplied data are the authority. Label every inference as an inference; if the spec is silent, say so instead of inventing a requirement.
- Quote numbers, units, and boundary words (at least, at most, inclusive, before/after) exactly.
- Read-only: do not fix data, write code, or split work into tasks here. Stay out of material the user has excluded.

## Workflow

1. Read the whole spec, including appendices, examples, and notes from users or stakeholders. Such notes often imply checks the requirement list does not state ("tell me when it is impossible", "I need to trust this number", "only approved results are visible", "the data is maintained by hand").
2. If data is supplied, audit it (read-only, standard library only):
   ```bash
   python3 -I <this-skill-dir>/scripts/data_audit.py <data-dir>
   ```
   It reports per-file shape, column types, value sets, and suspicious rows with `file:line`: unit suffixes, empty or non-numeric values, duplicates, case variants, zeros and negatives, BOM/CRLF, ragged grid rows, rare symbols. Then check what it cannot: IDs that do not exist in the referenced file, values outside ranges the spec defines, codes missing from the spec's legend.
3. Reply with the brief below. Write it to a file (for example `docs/requirements.md`) when the user asks for a document or when other people or agents will build on it.

## Brief

Keep it short; use the user's language.

Always:

1. **What it is**: one sentence on who uses it and what they get; one on what is out of scope.
2. **Components**: an ASCII diagram from inputs through each component to outputs. Under each component, the one question it answers, for example `importer: which rows are valid?` and `report: what is the total per month?`.
3. **Requirements**: `ID | requirement | source | done when (observable) | mandatory? | how to verify`. Reuse IDs from the spec when present.
4. **Rules and constraints**: exact value, unit, boundary inclusivity, and where the value lives (config, data, code).
5. **Open interpretations**: each with a recommended default and why; mark the ones the user must decide now.

Only when the spec or data has them:

6. **Data problems**: each finding with `file:line` and a proposed handling (exclude and report, normalize and record, or stop).
7. **Priorities and trade-offs**: the order of goals and tie-breakers when goals compete.
8. **Interface contract**: required output formats, files, or APIs, and what consumes them.
9. **Variants**: configurations, environments, or change cases the spec defines, what each changes, and what must be compared.
10. **First slice**: the smallest input-to-visible-output path, with its expected result when it can be worked out by hand.

When the user asks how parts relate, answer with a diagram first. When a term will appear on screen or in output, define it precisely, including the order of events in time.
