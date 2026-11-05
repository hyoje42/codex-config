#!/usr/bin/env python3
"""Read-only profile of a data folder (CSV, TSV, JSON, and text grids).

Usage: python3 -I data_audit.py <data_dir> [--max-examples N]

Reports, per file, the facts an implementer needs before writing a loader:
row counts, columns, inferred types, and suspicious rows with file:line.
For CSV/TSV records, line is the physical start line, including multiline headers.
It never modifies anything. Findings are hints, not verdicts: the spec
decides what counts as an error.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

NUM = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
NUM_WITH_UNIT = re.compile(r"^[+-]?\d+(\.\d+)?\s*[A-Za-z%가-힣]+$")
TIME = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


def classify(value: str) -> str:
    v = value.strip()
    if v == "":
        return "empty"
    if NUM.match(v):
        return "num"
    if TIME.match(v):
        return "time"
    if NUM_WITH_UNIT.match(v):
        return "num+unit"
    return "text"


def read_text(path: Path) -> tuple[str, list[str]]:
    raw = path.read_bytes()
    notes = []
    if raw.startswith(b"\xef\xbb\xbf"):
        notes.append("UTF-8 BOM at start of file")
        raw = raw[3:]
    if b"\r\n" in raw:
        notes.append("CRLF line endings")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        notes.append(f"not valid UTF-8 ({exc}); decoded with replacement")
        text = raw.decode("utf-8", errors="replace")
    return text, notes


def audit_csv(path: Path, max_ex: int) -> None:
    text, notes = read_text(path)
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    reader = csv.reader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows: list[tuple[int, list[str]]] = []
    start_line = 1
    for row in reader:
        rows.append((start_line, row))
        start_line = reader.line_num + 1
    if not rows:
        print("  empty file")
        return
    _, header = rows[0]
    body = rows[1:]
    print(f"  rows: {len(body)} (+header)  columns: {len(header)}")
    for n in notes:
        print(f"  ! {n}")
    padded = [h for h in header if h != h.strip()]
    if padded:
        print(f"  ! header cells with surrounding spaces: {padded}")
    issues: list[str] = []
    kinds = [Counter() for _ in header]
    seen_first: dict[str, tuple[int, tuple[str, ...]]] = {}
    seen_rows: dict[tuple[str, ...], int] = {}
    for i, row in body:
        if not any(c.strip() for c in row):
            issues.append(f"{path.name}:{i} blank row")
            continue
        if len(row) != len(header):
            issues.append(f"{path.name}:{i} has {len(row)} fields, header has {len(header)}: {row}")
        key = tuple(c.strip() for c in row)
        if key in seen_rows:
            issues.append(f"{path.name}:{i} exact duplicate of line {seen_rows[key]}")
        seen_rows.setdefault(key, i)
        first = row[0].strip() if row else ""
        if first in seen_first:
            first_line, first_key = seen_first[first]
            if key != first_key:
                issues.append(f"{path.name}:{i} duplicate id '{first}' (first at line {first_line})")
        seen_first.setdefault(first, (i, key))
        for j, cell in enumerate(row[: len(header)]):
            kinds[j][classify(cell)] += 1
            if cell != cell.strip() and cell.strip():
                issues.append(f"{path.name}:{i} column '{header[j]}' has surrounding spaces: {cell!r}")
    print("  column types (counts):")
    for j, h in enumerate(header):
        k = dict(kinds[j])
        print(f"    {h.strip()}: {k}")
        col = h.strip()
        dominant = kinds[j].most_common(1)[0][0] if kinds[j] else None
        if dominant in ("num", "time"):
            # Group mismatches by kind so a legitimately optional column stays one line.
            by_kind: dict[str, list[tuple[int, str]]] = {}
            for i, row in body:
                if j < len(row) and classify(row[j]) != dominant:
                    by_kind.setdefault(classify(row[j]), []).append((i, row[j]))
            for kind, hits in by_kind.items():
                lines = [i for i, _ in hits]
                sample = ", ".join(f"{i}:{v!r}" for i, v in hits[:max_ex])
                issues.append(
                    f"{path.name}: column '{col}' expected {dominant}, {len(hits)} row(s) are {kind} "
                    f"(lines {lines[:max_ex * 2]}{' ...' if len(lines) > max_ex * 2 else ''}; e.g. {sample})"
                )
        # Low-cardinality text columns: show the value set, odd spellings show up here.
        values = Counter(row[j].strip() for _, row in body if j < len(row))
        if dominant == "text" and len(values) <= 8:
            print(f"      values: {dict(values)}")
            folded: dict[str, set[str]] = {}
            for v in values:
                folded.setdefault(v.casefold(), set()).add(v)
            for variants in folded.values():
                if len(variants) > 1:
                    issues.append(f"{path.name}: column '{col}' has case variants {sorted(variants)}")
        if dominant == "num":
            num_rows = [(i, float(row[j])) for i, row in body if j < len(row) and classify(row[j]) == "num"]
            if num_rows:
                nums = [x for _, x in num_rows]
                print(f"      range: {min(nums)} .. {max(nums)}")
                neg = [i for i, x in num_rows if x < 0]
                if neg:
                    issues.append(f"{path.name}: column '{col}' has negative values at lines {neg[:max_ex]}")
                zero = [i for i, x in num_rows if x == 0]
                if zero and len(zero) < len(nums):
                    issues.append(f"{path.name}: column '{col}' has zero at lines {zero[:max_ex]} (check if allowed)")
    report(issues, max_ex)


def audit_json(path: Path, max_ex: int) -> None:
    text, notes = read_text(path)
    for n in notes:
        print(f"  ! {n}")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"  ! invalid JSON: {exc}")
        return
    if data is None:
        print("  ! top-level value is null")
        return

    def walk(obj, prefix="", depth=0):
        if depth > 3:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                shown = json.dumps(v, ensure_ascii=False)
                if isinstance(v, (dict, list)):
                    print(f"  {prefix}{k}: {type(v).__name__}({len(v)})")
                    walk(v, prefix + "  ", depth + 1)
                else:
                    print(f"  {prefix}{k} = {shown[:80]}")
                    if v is None:
                        print(f"  {prefix}  ! null value")
        elif isinstance(obj, list) and obj:
            print(f"  {prefix}[0] example: {json.dumps(obj[0], ensure_ascii=False)[:120]}")
            kinds = Counter(type(x).__name__ for x in obj)
            if len(kinds) > 1:
                print(f"  {prefix}! mixed element types: {dict(kinds)}")

    walk(data)


def audit_grid(path: Path, max_ex: int) -> None:
    text, notes = read_text(path)
    for n in notes:
        print(f"  ! {n}")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    widths = Counter(len(l.rstrip("\r")) for l in lines)
    width = widths.most_common(1)[0][0] if widths else 0
    chars = Counter(ch for l in lines for ch in l.rstrip("\r"))
    print(f"  lines: {len(lines)}  most common width: {width}  widths: {dict(widths)}")
    print(f"  symbols: {dict(chars.most_common())}")
    issues = []
    for y, l in enumerate(lines):
        l = l.rstrip("\r")
        if len(l) != width:
            issues.append(f"{path.name}:{y + 1} (y={y}) width {len(l)} != {width}")
        if l != l.rstrip(" \t"):
            issues.append(f"{path.name}:{y + 1} (y={y}) trailing whitespace")
    rare = [c for c, n in chars.items() if n <= 3]
    for c in rare:
        for y, l in enumerate(lines):
            for x, ch in enumerate(l):
                if ch == c:
                    issues.append(f"{path.name}:{y + 1} rare symbol {c!r} at (x={x}, y={y})")
    print("  (compare the symbol set with the legend in the spec; unknown symbols need a decision)")
    report(issues, max_ex)


def report(issues: list[str], max_ex: int) -> None:
    if not issues:
        print("  no suspicious rows found by generic checks")
        return
    print(f"  suspicious: {len(issues)}")
    for s in issues[: max_ex * 4]:
        print(f"    - {s}")
    if len(issues) > max_ex * 4:
        print(f"    ... {len(issues) - max_ex * 4} more")


def looks_like_grid(path: Path) -> bool:
    text, _ = read_text(path)
    lines = [l for l in text.splitlines() if l]
    return len(lines) >= 3 and all(" " not in l.strip() for l in lines[:5]) and "," not in text[:200]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--max-examples", type=int, default=5)
    args = ap.parse_args()
    root = Path(args.data_dir)
    if not root.is_dir():
        ap.error(f"입력 경로가 존재하는 디렉터리가 아닙니다: {root}")
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        print(f"\n== {rel}")
        suffix = path.suffix.lower()
        try:
            if suffix in (".csv", ".tsv"):
                audit_csv(path, args.max_examples)
            elif suffix == ".json":
                audit_json(path, args.max_examples)
            elif suffix == ".txt" and looks_like_grid(path):
                audit_grid(path, args.max_examples)
            else:
                print(f"  skipped ({path.stat().st_size} bytes); read it directly if relevant")
        except Exception as exc:  # keep auditing other files
            print(f"  ! audit failed: {exc}")


if __name__ == "__main__":
    main()
