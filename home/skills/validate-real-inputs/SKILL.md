---
name: validate-real-inputs
description: "Verify and harden an input path that passes with fixtures or mocks but fails on real files, API responses, or batch data: trace each record from read to output, account for accepted, excluded, and duplicated records with reasons, and check reruns, stale results, and partial failures. Use when wiring real data in place of demo data, after an input format change, or when records go missing, duplicate, or partially fail. Correctness of the formulas themselves (verify-computation) and broad production readiness are out of scope."
---

# Validate Real Inputs

Trace how real input is read, normalized, filtered, and reflected in the result. Keep separate "the file was read" or "the request succeeded" from "the right data was processed".

## 1. Confirm representative inputs and the execution path

Find the input paths, settings, and fixture injection points the code actually uses. Check whether a real run still silently falls back to a hidden mock, default sample, or demo dataset. From the real inputs you are allowed to use, pick normal and problematic examples; de-identify sensitive values before they become regression fixtures.

Find the differences between fixtures and real input: types, empty values, ID formats, record counts, page counts, cross-file references, date and time ranges, encodings (BOM, line endings), units written inside values. If a data audit of the raw files already exists (for example from `spec-brief`), reconcile its findings with what the loader actually does. Scope the investigation to the observed differences and to what the code assumes.

## 2. Make every record's fate explainable

Find where records disappear or multiply along input → parse → normalize → exclude or deduplicate → compute or store → output. State the unit of each count (rows, entities, directional demands) for raw, accepted, excluded, and duplicate records. If a transformation is one-to-many or aggregates, reconcile by keys and rules instead of matching totals.

Distinguish bad rows, broken files or responses, and invalid required settings, and decide from the current contract whether partial acceptance or a full stop is correct. Also distinguish a required input that is missing or unreadable (file absent, malformed, `null` where an object is required) from one that is valid but empty: whether an empty batch is normal is a question for the input contract. A missing or unreadable required input must not produce a result reported as success. Every exclusion or correction must be traceable to a source location or ID with a reason, and visible where the product reports problems (a screen, a report file, a log). Check whether a silent default hides an input error.

## 3. Test the change and failure paths that apply

Reproduce each real-input problem as a minimal case through the public entry point. Keep small fixtures for fast regression, but inject the input choice explicitly. Do not switch the production default back to demo data to make tests pass.

Check only the cases that apply to the current path:

- **Rerun and retry**: processing the same input again accumulates, overwrites, or rejects duplicates as the contract says.
- **Stored or cached results**: after the input changes, new results reference the right input, and old results follow the stated keep-or-invalidate policy. Results from demo or sample data are not presented as current real results. Do not introduce a snapshot system unless it is needed.
- **Partial failure**: a failed input is not reported as success, and a previous output is not returned as the new result.
- **Pages and chunks**: termination conditions, duplicate keys, and the last partial batch do not cause loss or duplication.

If a real service must be called, stay within current permissions and use reads or isolated runs. Do not add production writes, reseeding, or deletes for the sake of validation.

## 4. Leave evidence of completion

Report the source and scope of the input used, accepted / excluded / transformed counts with reasons, reproduction commands, regression cases added, and input kinds still untested. If only recorded responses were used without a live connection, say so. Do not extend success on one real batch to "all inputs supported" or "production ready".
