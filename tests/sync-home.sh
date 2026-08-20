#!/bin/bash
#
# codex-diff-with-home / codex-sync-to-home 회귀 테스트.
#
# 임시 HOME과 repo 사본(fixture)에서 dry-run(diff)과 sync를 실행해 다음을 검증한다:
#   - dry-run은 ~/.codex·~/.agents·~/.bashrc에 아무것도 쓰지 않는다
#   - dry-run이 언급한 경로(변경/신규/config/고아·legacy·retired skill)가 sync에서 그대로 적용된다
#   - config.toml은 현재 파일의 머신별 키를 보존한 채 baseline+override가 merge된다
#   - 래퍼는 실제 값일 때만 ~/.bashrc에 한 번 설치되고, placeholder·파일 없음이면 설치하지 않는다
#   - sync 직후 diff는 "차이 없음", sync는 "변경 사항 없음"(멱등)
#   - 승인 프롬프트에 n을 주면 고아·legacy·retired는 건드리지 않는다
#
# 단언은 파일 시스템 결과·종료 코드·경로 언급 여부 위주로 둔다. 안내 문구·요약
# 포맷·프롬프트 개수가 바뀌어도 깨지지 않게 하기 위함이다(동작이 바뀔 때만 깨진다).
# 실제 ~/.codex·~/.agents·~/.bashrc는 건드리지 않는다.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT

fail() {
    echo "실패: $*" >&2
    exit 1
}
has()   { grep -Fq -- "$2" <<<"$1"; }    # has <text> <substring>
lacks() { ! grep -Fq -- "$2" <<<"$1"; }

# 디렉터리 전체를 경로+내용 해시로 스냅샷한다(변경 없음 판정용).
snapshot() {
    (cd "$1" && find . -type f | sort | while read -r f; do md5sum "$f"; done)
}

# 시나리오마다 새 fixture repo + HOME을 만든다. git 메타·백업·실제 local 값은 복사하지 않는다.
new_fixture() {  # new_fixture <name>  → FX(repo) / HOME_DIR / CX(~/.codex) / AG(~/.agents/skills)
    FX="$TEST_ROOT/$1/repo"
    HOME_DIR="$TEST_ROOT/$1/home"
    CX="$HOME_DIR/.codex"
    AG="$HOME_DIR/.agents/skills"
    mkdir -p "$FX" "$CX" "$AG"
    rsync -a --exclude='/.git' --exclude='/_backup' --exclude='/local/*' "$REPO/" "$FX/"
    mkdir -p "$FX/local"
    cp "$REPO"/local/*.example "$FX/local/" 2>/dev/null || true
}
# rsync는 크기+mtime으로 같은 파일을 판정하므로, 미리 둔 HOME 파일은 과거 mtime으로 둔다.
age_home() { find "$HOME_DIR" -type f -exec touch -d '2020-01-01 00:00:00' {} +; }

run_diff() { HOME="$HOME_DIR" "$FX/codex-diff-with-home" 2>&1; }
# run_sync <y|n>: 모든 승인 프롬프트에 같은 답을 넉넉히 흘려 넣는다(프롬프트 수에 의존하지 않음).
run_sync() { printf "$1\n%.0s" {1..20} | HOME="$HOME_DIR" "$FX/codex-sync-to-home" 2>&1; }

WRAPPER_MARKER='# >>> codex proxy wrapper >>>'
# 실제 래퍼 파일을 placeholder 없이 만든다.
make_real_wrapper() {
    sed 's/<PROXY_HOST>:<PORT>/proxy.test:8080/g; s#/absolute/path/to/ca-bundle.pem#/etc/ssl/test-ca.pem#; s/<no-proxy-domains>/.test/g' \
        "$FX/local/codex-proxy-wrapper.sh.example" > "$FX/local/codex-proxy-wrapper.sh"
    grep -q '<PROXY_HOST>' "$FX/local/codex-proxy-wrapper.sh" && fail "테스트 래퍼에 placeholder가 남았습니다."
    return 0
}

###############################################################################
echo "[1] 전체: 변경·신규·config merge·래퍼 설치·고아/legacy/retired skill → dry-run 언급 = sync 적용"
new_fixture s1
mkdir -p "$CX/skills/.system" "$CX/skills/unrelated-legacy" "$CX/skills/review-pr" "$CX/skills/write-review" \
         "$AG/unrelated" "$AG/read-review" "$AG/review-pr"
echo sys > "$CX/skills/.system/marker"                               # Codex 소유: 보존
echo ul  > "$CX/skills/unrelated-legacy/SKILL.md"                    # 관리 밖 legacy: 보존
cp -a "$FX/home/skills/review-pr/." "$CX/skills/review-pr/"          # legacy 경로의 관리 skill
echo retired > "$CX/skills/write-review/SKILL.md"                    # retired(legacy 경로)
echo un > "$AG/unrelated/SKILL.md"                                   # 공유 경로의 다른 skill: 보존
echo retired > "$AG/read-review/SKILL.md"                            # retired(공유 경로)
cp -a "$FX/home/skills/review-pr/." "$AG/review-pr/"
echo "stale line" >> "$AG/review-pr/SKILL.md"                        # 변경
echo orphan > "$AG/review-pr/orphan.md"                              # 관리 skill 안의 고아
cp "$FX/home/AGENTS.md" "$CX/AGENTS.md"; echo "stale line" >> "$CX/AGENTS.md"   # 변경
printf 'model = "old-model"\n\n[projects."/work/x"]\ntrusted = true\n' > "$CX/config.toml"   # 머신별 키 포함
printf 'model = "override-model"\n\n[features]\ncodex_git_commit = true\n' > "$FX/local/config.override.toml"
make_real_wrapper
echo "# existing bashrc" > "$HOME_DIR/.bashrc"
age_home

before="$(snapshot "$HOME_DIR")"
out="$(run_diff)"
[ "$(snapshot "$HOME_DIR")" = "$before" ]   || fail "dry-run이 HOME을 변경했습니다."
for p in config.toml AGENTS.md review-pr/SKILL.md handoff/SKILL.md review-pr/orphan.md \
         .codex/skills/review-pr .agents/skills/read-review .codex/skills/write-review; do
    has "$out" "$p" || fail "dry-run이 $p 를 언급하지 않았습니다."
done
has "$out" 'override-model'                 || fail "dry-run의 config.toml 내용에 override 값이 없습니다(merge 결과로 비교해야 함)."
lacks "$out" "unrelated"                    || fail "관리 밖 skill을 언급했습니다."
lacks "$out" ".system"                      || fail "Codex 소유 .system을 언급했습니다."

run_sync y >/dev/null
cmp -s "$CX/AGENTS.md" "$FX/home/AGENTS.md"                          || fail "~/.codex/AGENTS.md가 갱신되지 않았습니다."
cmp -s "$AG/review-pr/SKILL.md" "$FX/home/skills/review-pr/SKILL.md" || fail "~/.agents skill이 갱신되지 않았습니다."
[ -f "$AG/handoff/SKILL.md" ]                                        || fail "신규 skill이 설치되지 않았습니다."
[ ! -e "$CX/skills/handoff" ]                                        || fail "skill이 deprecated ~/.codex/skills에 설치됐습니다."
grep -q '^model = "override-model"' "$CX/config.toml"                || fail "config.toml에 override 값이 없습니다."
grep -q 'trusted = true' "$CX/config.toml"                           || fail "config.toml의 머신별 키(project trust)가 사라졌습니다."
grep -q 'codex_git_commit = true' "$CX/config.toml"                  || fail "config.toml에 override 테이블 값이 없습니다."
if ! python3 - "$FX/home/config.toml" "$CX/config.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as source_file:
    source = tomllib.load(source_file)
with open(sys.argv[2], "rb") as target_file:
    target = tomllib.load(target_file)

if source.get("developer_instructions") != target.get("developer_instructions"):
    raise SystemExit(1)
PY
then
    fail "developer_instructions가 ~/.codex/config.toml에 정확히 전달되지 않았습니다."
fi
grep -qF "$WRAPPER_MARKER" "$HOME_DIR/.bashrc"                       || fail "~/.bashrc에 래퍼가 설치되지 않았습니다."
grep -qF 'proxy.test:8080' "$HOME_DIR/.bashrc"                       || fail "~/.bashrc에 실제 래퍼 값이 없습니다."
head -1 "$HOME_DIR/.bashrc" | grep -qF '# existing bashrc'           || fail "기존 ~/.bashrc 내용이 보존되지 않았습니다."
[ ! -e "$AG/review-pr/orphan.md" ]                                   || fail "고아 파일이 삭제되지 않았습니다."
[ ! -e "$AG/read-review" ]                                           || fail "공유 경로 retired skill이 제거되지 않았습니다."
[ ! -e "$CX/skills/write-review" ]                                   || fail "legacy 경로 retired skill이 제거되지 않았습니다."
[ ! -e "$CX/skills/review-pr" ]                                      || fail "legacy 경로 관리 skill이 제거되지 않았습니다."
[ -f "$CX/skills/.system/marker" ]                                   || fail "Codex 소유 .system이 손상됐습니다."
[ -f "$CX/skills/unrelated-legacy/SKILL.md" ]                        || fail "관리 밖 legacy skill이 손상됐습니다."
[ -f "$AG/unrelated/SKILL.md" ]                                      || fail "공유 경로의 다른 skill이 손상됐습니다."
find "$FX/_backup" -path '*/review-pr/orphan.md' -print -quit | grep -q .  || fail "삭제한 고아 파일의 백업이 없습니다."
find "$FX/_backup" -name bashrc -print -quit | grep -q .                   || fail "~/.bashrc 백업이 없습니다."
[ "$(grep -c 'old-model' "$(find "$FX/_backup" -maxdepth 2 -name config.toml -print -quit)")" -ge 1 ] \
                                                                     || fail "config.toml 이전 값 백업이 없습니다."

out="$(run_diff)";   has "$out" "차이 없음"     || fail "sync 직후 dry-run이 깨끗하지 않습니다."
out="$(run_sync y)"; has "$out" "변경 사항 없음" || fail "sync 직후 재실행이 멱등하지 않습니다."
[ "$(grep -cF "$WRAPPER_MARKER" "$HOME_DIR/.bashrc")" -eq 1 ]        || fail "래퍼가 ~/.bashrc에 중복 설치됐습니다."

###############################################################################
echo "[2] 승인 거부(n): 고아·retired·legacy는 그대로, 파일 sync는 적용"
new_fixture s2
mkdir -p "$CX/skills/review-pr" "$CX/skills/read-review" "$AG/review-pr"
cp -a "$FX/home/skills/review-pr/." "$CX/skills/review-pr/"
echo r > "$CX/skills/read-review/SKILL.md"
cp -a "$FX/home/skills/review-pr/." "$AG/review-pr/"; echo orphan > "$AG/review-pr/orphan.md"
run_sync n >/dev/null
[ -e "$AG/review-pr/orphan.md" ]   || fail "거부했는데 고아 파일이 삭제됐습니다."
[ -e "$CX/skills/read-review" ]    || fail "거부했는데 retired skill이 삭제됐습니다."
[ -e "$CX/skills/review-pr" ]      || fail "거부했는데 legacy skill이 삭제됐습니다."
[ -f "$CX/AGENTS.md" ]             || fail "home/ 파일이 설치되지 않았습니다."
[ -f "$AG/handoff/SKILL.md" ]      || fail "skill이 ~/.agents/skills에 설치되지 않았습니다."

###############################################################################
echo "[3] placeholder 래퍼 + config.toml 없음 + ~/.bashrc 없음"
new_fixture s3
cp "$FX/local/codex-proxy-wrapper.sh.example" "$FX/local/codex-proxy-wrapper.sh"   # placeholder 그대로
out="$(run_diff)"; has "$out" "config.toml"  || fail "config.toml 신규를 언급하지 않았습니다."
run_sync y >/dev/null
[ ! -e "$HOME_DIR/.bashrc" ]       || fail "placeholder 래퍼를 ~/.bashrc에 설치했습니다."
"$FX/codex-merge-config" "$FX/home/config.toml" "$FX/local/config.override.toml" "$CX/config.toml.missing" > "$TEST_ROOT/s3-merged.toml"
cmp -s "$CX/config.toml" "$TEST_ROOT/s3-merged.toml" || fail "신규 config.toml이 merge 결과와 다릅니다."
out="$(run_diff)";   has "$out" "차이 없음"     || fail "sync 직후 dry-run이 깨끗하지 않습니다."
out="$(run_sync y)"; has "$out" "변경 사항 없음" || fail "placeholder 상태에서 재실행이 멱등하지 않습니다."

###############################################################################
echo "[4] 실제 래퍼 없음(.example만): ~/.bashrc를 만들지 않음"
new_fixture s4
run_sync y >/dev/null
[ ! -e "$HOME_DIR/.bashrc" ]       || fail "래퍼 파일이 없는데 ~/.bashrc를 만들었습니다."
[ -f "$CX/AGENTS.md" ]             || fail "home/ 파일이 설치되지 않았습니다."

###############################################################################
echo "[5] 래퍼/옵션: diff = sync --dry-run, 알 수 없는 옵션은 exit 2"
new_fixture s5
a="$(run_diff)"; b="$(HOME="$HOME_DIR" "$FX/codex-sync-to-home" --dry-run 2>&1)"
[ "$a" = "$b" ]                    || fail "codex-diff-with-home과 --dry-run 출력이 다릅니다."
set +e; HOME="$HOME_DIR" "$FX/codex-sync-to-home" --bogus >/dev/null 2>&1; rc=$?; set -e
[ "$rc" -eq 2 ]                    || fail "알 수 없는 옵션이 exit 2가 아닙니다(exit $rc)."
[ -z "$(ls -A "$CX")" ] && [ -z "$(ls -A "$AG")" ] || fail "dry-run/옵션 오류가 홈 대상에 파일을 썼습니다."

echo "통과: codex diff/sync의 미리보기·적용·멱등성·래퍼 동작을 확인했습니다."
