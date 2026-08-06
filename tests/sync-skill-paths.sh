#!/bin/bash

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
FIXTURE_REPO="$TEST_ROOT/codex-config"
TEST_HOME="$TEST_ROOT/home"
SYNC_LOG="$TEST_ROOT/sync.log"

cleanup() {
    rm -rf -- "$TEST_ROOT"
}
trap cleanup EXIT

fail() {
    echo "실패: $*" >&2
    exit 1
}

mkdir -p "$FIXTURE_REPO" "$TEST_HOME/.codex/skills/.system" \
    "$TEST_HOME/.codex/skills/unrelated-legacy" \
    "$TEST_HOME/.codex/skills/write-review" \
    "$TEST_HOME/.agents/skills/unrelated" \
    "$TEST_HOME/.agents/skills/read-review"

# Copy only the testable repo payload; do not copy git metadata, backups, or real local overrides.
rsync -a \
    --exclude='/.git' \
    --exclude='/_backup' \
    --exclude='/local/config.override.toml' \
    --exclude='/local/codex-proxy-wrapper.sh' \
    "$REPO/" "$FIXTURE_REPO/"

printf 'system cache\n' > "$TEST_HOME/.codex/skills/.system/marker"
printf 'unrelated legacy skill\n' > "$TEST_HOME/.codex/skills/unrelated-legacy/SKILL.md"
printf 'unrelated shared skill\n' > "$TEST_HOME/.agents/skills/unrelated/SKILL.md"
printf 'retired shared skill\n' > "$TEST_HOME/.agents/skills/read-review/SKILL.md"
printf 'retired legacy skill\n' > "$TEST_HOME/.codex/skills/write-review/SKILL.md"
cp -a "$FIXTURE_REPO/home/skills/review-pr" "$TEST_HOME/.codex/skills/review-pr"

diff_output="$(HOME="$TEST_HOME" "$FIXTURE_REPO/codex-diff-with-home")"
grep -Fq "~/.codex/skills/review-pr/" <<<"$diff_output" ||
    fail "deprecated 경로의 중복 관리 skill을 감지하지 못했습니다."
grep -Fq "~/.agents/skills/read-review/" <<<"$diff_output" ||
    fail "공유 경로의 퇴역 관리 skill을 감지하지 못했습니다."
grep -Fq "~/.codex/skills/write-review/" <<<"$diff_output" ||
    fail "deprecated 경로의 퇴역 관리 skill을 감지하지 못했습니다."

printf 'y\ny\n' | HOME="$TEST_HOME" "$FIXTURE_REPO/codex-sync-to-home" > "$SYNC_LOG"

[ -f "$TEST_HOME/.agents/skills/review-pr/SKILL.md" ] ||
    fail "관리 skill이 ~/.agents/skills에 설치되지 않았습니다."
[ ! -e "$TEST_HOME/.codex/skills/review-pr" ] ||
    fail "관리 skill이 deprecated ~/.codex/skills에 설치됐습니다."
[ -f "$TEST_HOME/.codex/AGENTS.md" ] ||
    fail "Codex 전역 지시문이 ~/.codex에 설치되지 않았습니다."
[ -f "$TEST_HOME/.codex/config.toml" ] ||
    fail "config.toml merge 결과가 ~/.codex에 생성되지 않았습니다."
[ -f "$TEST_HOME/.codex/skills/.system/marker" ] ||
    fail "Codex 소유 .system cache가 손상됐습니다."
[ -f "$TEST_HOME/.codex/skills/unrelated-legacy/SKILL.md" ] ||
    fail "repo가 관리하지 않는 legacy skill이 손상됐습니다."
[ -f "$TEST_HOME/.agents/skills/unrelated/SKILL.md" ] ||
    fail "공유 경로의 다른 skill이 손상됐습니다."
[ ! -e "$TEST_HOME/.agents/skills/read-review" ] ||
    fail "공유 경로의 퇴역 관리 skill이 제거되지 않았습니다."
[ ! -e "$TEST_HOME/.codex/skills/write-review" ] ||
    fail "deprecated 경로의 퇴역 관리 skill이 제거되지 않았습니다."
find "$FIXTURE_REPO/_backup" \
    -path '*/legacy-codex-skills/review-pr/SKILL.md' -print -quit |
    grep -q . || fail "삭제한 legacy skill의 백업이 생성되지 않았습니다."
find "$FIXTURE_REPO/_backup" \
    -path '*/retired-agents-skills/read-review/SKILL.md' -print -quit |
    grep -q . || fail "공유 경로 퇴역 skill의 백업이 생성되지 않았습니다."
find "$FIXTURE_REPO/_backup" \
    -path '*/retired-legacy-codex-skills/write-review/SKILL.md' -print -quit |
    grep -q . || fail "deprecated 경로 퇴역 skill의 백업이 생성되지 않았습니다."

diff_output="$(HOME="$TEST_HOME" "$FIXTURE_REPO/codex-diff-with-home")"
grep -Fq "차이 없음" <<<"$diff_output" ||
    fail "sync 직후 diff가 깨끗하지 않습니다."
if grep -Fq "unrelated" <<<"$diff_output"; then
    fail "공유 경로의 다른 skill을 관리 대상으로 보고했습니다."
fi

echo "통과: Codex skill sync 경로와 공유 디렉터리 보호를 확인했습니다."
