#!/bin/bash

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
CURRENT="$TEST_ROOT/current.toml"
BASELINE="$TEST_ROOT/baseline.toml"
OVERRIDE="$TEST_ROOT/override.toml"
BASELINE_RESULT="$TEST_ROOT/baseline-result.toml"
OVERRIDE_RESULT="$TEST_ROOT/override-result.toml"

cleanup() {
    rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT

fail() {
    echo "실패: $*" >&2
    exit 1
}

cat > "$CURRENT" <<'TOML'
developer_instructions = "현재 머신 문체"
machine_only = "보존할 값"

[projects."/work/example"]
trusted = true
TOML

cat > "$BASELINE" <<'TOML'
developer_instructions = """\n한국어 첫 줄
"큰따옴표"와 C:\\tools\\codex
연속 따옴표: \"\"\"
탭:\t제어 문자
끝 줄\n"""
baseline_only = "공통 값"

[features]
codex_git_commit = false
TOML

cat > "$OVERRIDE" <<'TOML'
developer_instructions = "머신별 대체 문체"

[features]
codex_git_commit = true
TOML

"$REPO/codex-merge-config" "$BASELINE" "" "$CURRENT" > "$BASELINE_RESULT"
"$REPO/codex-merge-config" "$BASELINE" "$OVERRIDE" "$CURRENT" > "$OVERRIDE_RESULT"

if ! python3 - "$CURRENT" "$BASELINE" "$OVERRIDE" "$BASELINE_RESULT" "$OVERRIDE_RESULT" <<'PY'
import sys
import tomllib


def load(path: str) -> tuple[dict, str]:
    with open(path, "rb") as file:
        data = tomllib.load(file)
    with open(path, encoding="utf-8") as file:
        return data, file.read()


current, _ = load(sys.argv[1])
baseline, _ = load(sys.argv[2])
override, _ = load(sys.argv[3])
baseline_result, baseline_text = load(sys.argv[4])
override_result, _ = load(sys.argv[5])

assert baseline_result["machine_only"] == current["machine_only"]
assert baseline_result["projects"] == current["projects"]
assert baseline_result["baseline_only"] == baseline["baseline_only"]
assert baseline_result["developer_instructions"] == baseline["developer_instructions"]
assert baseline_result["features"]["codex_git_commit"] is False

assert override_result["machine_only"] == current["machine_only"]
assert override_result["projects"] == current["projects"]
assert override_result["developer_instructions"] == override["developer_instructions"]
assert override_result["features"]["codex_git_commit"] is True

assert 'developer_instructions = """' in baseline_text
assert "한국어 첫 줄\n" in baseline_text
assert 'developer_instructions = "\\n' not in baseline_text
PY
then
    fail "config merge의 보존·우선순위·multiline round-trip 검증에 실패했습니다."
fi

echo "통과: config merge의 보존·우선순위와 multiline 문자열 round-trip을 확인했습니다."
