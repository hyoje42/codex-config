# Codex 설정 관리 저장소

Codex를 더 편하게 사용하기 위한 커스텀 skill과 전역 지시문을 만들고 Codex가 읽는 홈 경로에 동기화하는 저장소. 전역 지시문·config는 `~/.codex/`, user skill은 `~/.agents/skills/`에 반영한다.

## 구조

- `home/` — 추적되는 sync 원본. `skills/`를 제외한 경로는 `~/.codex/` 레이아웃을 미러링하고, `config.toml`은 merge로 적용한다.
  - `home/AGENTS.md` — Codex의 기본 응답 언어와 공통 작업 규칙 (`~/.codex/AGENTS.md`로 sync). `~/.codex/rules/`는 지시문으로 로드되지 않는다. 이 파일은 sync payload이며, repo meta 문서가 아니다.
  - `home/config.toml` — 공통 Codex baseline과 한국어 문체용 `developer_instructions`. 단순 복사가 아니라 현재 `~/.codex/config.toml` 위에 merge된다(아래 참고).
  - `home/skills/` — 커스텀 skill 정의. sync 대상은 공식 user skill 경로인 `~/.agents/skills/`다. `$CODEX_HOME/skills`는 [공식 loader](https://github.com/openai/codex/blob/main/codex-rs/core-skills/src/loader.rs)가 하위 호환용 deprecated 경로로만 유지한다.
- `local/` — **머신 종속 설정의 템플릿을 두는 곳 (sync 대상 아님).** 루트 `.gitignore`가 `local/*`를 무시하고 `*.example` 템플릿만 추적한다. 실제 머신 값 파일(`config.override.toml`·`codex-proxy-wrapper.sh` 등)은 커밋되지 않는다.
  - `local/config.override.toml.example` — 머신별 `config.toml` override 템플릿. 실제 값은 `local/config.override.toml`(gitignore됨)에 둔다.
  - `local/codex-proxy-wrapper.sh.example` — 프록시 환경 로그인용 `~/.bashrc` codex 래퍼 템플릿. 실제 값은 `local/codex-proxy-wrapper.sh`(gitignore됨)에 채우고, sync가 `~/.bashrc`에 설치한다(아래 참고).
- `skill-authoring.md` — skill 작성·이식 가이드
- `outdated/` — 퇴역한 skill·rule의 기록용 보관소. **sync 대상 아님.**
- `README.md`(이 문서) — 이 repo 설명. / `AGENTS.md`(= `CLAUDE.md`) — agent 작업 규칙. 둘 다 **sync 대상 아님.**
- `_backup/` — `~/.codex`와 이 repo가 관리하는 `~/.agents/skills` 동기화 전 백업. **수정 금지.**

## 스크립트

- `codex-sync-to-home` — `home/skills/`는 `~/.agents/skills/`, 나머지는 `~/.codex/`에 반영한다. `config.toml`은 현재 `~/.codex/config.toml` + `home/config.toml` + 선택적 `local/config.override.toml`을 merge해서 쓴다. 또한 `local/codex-proxy-wrapper.sh`(실제 값)가 있고 `~/.bashrc`에 래퍼가 아직 없으면 한 번 설치한다(아래 참고). **사용자가 명시적으로 지시했을 때만 실행한다.**
- `codex-diff-with-home` — `home/`과 두 실제 대상(`~/.codex/`, `~/.agents/skills/`)의 차이 확인. `config.toml`은 실제 sync 때 만들어질 merge 결과와 비교하고, codex 래퍼는 설치/보존 여부를 안내한다. 실체는 `codex-sync-to-home --dry-run`의 얇은 래퍼라, 무엇이 바뀌는지 계산하는 로직(래퍼 판정·legacy/retired skill 탐지 포함)은 `codex-sync-to-home` 한 곳에만 있다.
- `codex-merge-config` — `config.toml` merge helper. `codex-sync-to-home`/`codex-diff-with-home`에서 호출하며, 줄바꿈이 있는 문자열은 읽기 쉬운 TOML multiline basic string으로 정규화한다.
- `tests/config-merge.sh` — current + baseline + override의 보존·우선순위와 multiline 문자열 round-trip을 임시 파일에서 검증한다.
- `tests/sync-home.sh` — 임시 HOME과 repo 사본에서 diff/sync를 실행해, dry-run이 아무것도 쓰지 않는지·dry-run이 보고한 항목(config merge·`developer_instructions` 전달·래퍼 판정·skill 경로·공유 디렉터리 보호·고아/legacy/retired skill 포함)이 sync에서 그대로 적용되는지·sync 직후 재실행이 멱등한지 검증한다. 실제 `~/.codex`·`~/.agents`·`~/.bashrc`는 건드리지 않는다.

## 작업 흐름

1. 공통 설정은 `home/`(`AGENTS.md`·`config.toml`·`skills/`)에서, 머신 종속 값은 `local/config.override.toml`·`~/.codex/config.toml`에서 수정한다. skill 원본은 계속 `home/skills/`에서 관리한다.
2. `./codex-diff-with-home`으로 차이를 확인한다.
3. 필요할 때 `./codex-sync-to-home`으로 `~/.codex/`에 반영한다.
4. `git commit`으로 변경 이력을 남긴다(`local/`의 실제 머신 값은 커밋되지 않는다).

## config.toml merge

Codex의 `config.toml`은 공통으로 맞추고 싶은 값과 머신마다 다른 값이 섞여 있고, Codex가 project trust 같은 항목을 계속 추가할 수 있다. 그래서 이 repo는 `home/config.toml`을 공통 baseline으로 두되, 파일 전체를 단순 복사하지 않고 sync 시점에 merge한다.

merge 순서:

1. 현재 `~/.codex/config.toml` (없으면 빈 TOML)
2. `home/config.toml` (공통 baseline, 커밋)
3. `local/config.override.toml` (선택, gitignore됨)

동작:

- 테이블은 재귀적으로 병합한다.
- 스칼라/배열은 뒤 레이어가 이긴다. 즉 같은 키가 이미 있으면 `home/config.toml` 또는 `local/config.override.toml` 값으로 교체하고, 없으면 추가한다.
- repo가 모르는 기존 머신별 값(project trust, Codex가 자동으로 추가한 값 등)은 보존한다.
- merge 결과는 정규화된 TOML로 다시 쓰므로 기존 `~/.codex/config.toml`의 주석/서식은 보존하지 않는다. 줄바꿈이 있는 문자열은 escaped `\n`이 이어지는 한 줄 대신 multiline TOML로 출력하되, parse한 값은 정확히 유지한다.

머신별 override가 필요하면:

```bash
cp local/config.override.toml.example local/config.override.toml
```

그 뒤 실제 model·reasoning effort·project trust 등을 `local/config.override.toml`에 넣는다. 이 파일은 `.gitignore`로 커밋되지 않는다.

## developer_instructions와 AGENTS.md의 역할

`home/config.toml`의 `developer_instructions`는 Codex가 실제 `developer` role 메시지에 추가하는 범용 지침이다. Codex의 named output style이나 선택 가능한 style metadata가 아니다. 이 저장소에서는 역할을 다음과 같이 나눈다.

- `home/AGENTS.md`는 기본 응답 언어를 선택하고 파일 편집·도구 사용·커밋과 같은 작업 규칙을 정의한다.
- `developer_instructions`는 한국어로 작성하기로 선택된 자연어 문장의 문체 품질만 규정한다. 두 위치에 같은 문체 규칙을 반복하지 않는다.

`developer_instructions`는 하나의 scalar string이다. project config나 `local/config.override.toml`에서 같은 키를 정의하면 공통 본문과 합쳐지지 않고 문자열 전체가 교체된다. 머신별로 문체 지침을 의도적으로 끄거나 대체할 때만 override한다.

설정을 바꾼 뒤에는 새 Codex 세션에서 확인하고, 설치된 CLI가 지원하면 `codex debug prompt-input`으로 초기 prompt의 role과 주입 횟수를 점검한다. 이 검증은 초기 prompt 구성만 확인하며, compaction 뒤 지침이 다시 주입된다고 보장하지 않는다.

문체 본문은 한국어 형태론과 대조 예시의 정밀도를 유지하기 위해 이 저장소의 agent instruction 영어 기본 원칙에 대한 예외로 한국어를 사용한다. Claude의 `home/output-styles/fluent-korean.md`가 바뀌면 Codex 전용 범위 설명은 보존하고 본문의 차이만 수동으로 대조하여 반영한다.

## 머신 종속 설정 (프록시·CA 로그인 래퍼)

프록시 환경(기업 프록시, TLS 검사 방화벽 등)에서는 `codex login`이 토큰 교환 단계에서 실패할 수 있다. 프록시가 TLS를 가로채 자체 CA로 재서명하는데, codex 본체(로그인/OAuth/API)가 그 CA를 신뢰하지 못하기 때문이다. 이 프록시·CA 설정은 `config.toml`이 아니라 codex **실행 시점의 env**(`HTTPS_PROXY`·`CODEX_CA_CERTIFICATE` 등)로만 잡히므로 `~/.bashrc`의 `codex()` 래퍼로 주입한다. config.toml과 달리 실제 값이 `~/.bashrc`에 들어가야 하므로, **실제 값 파일을 `local/`에 두고 sync가 `~/.bashrc`에 append**한다.

- **셋업**: `local/codex-proxy-wrapper.sh.example` → `local/codex-proxy-wrapper.sh`로 복사(루트 `.gitignore`로 추적 안 됨) → placeholder(프록시 주소·CA 경로 등)를 이 환경의 실제 값으로 채움 → `./codex-sync-to-home` → `source ~/.bashrc`.
- **동작**: `~/.bashrc`에 래퍼 마커가 이미 있으면 보존 / 실제 파일이 없으면 아무것도 안 함(`.example`만으론 설치 안 함) / placeholder가 남아 있으면 설치 보류. `codex-diff-with-home`이 이 판정을 미리 안내한다.

## 동기화 위치

`home/`의 대상은 다음과 같이 나뉜다.

- `home/AGENTS.md` -> `~/.codex/AGENTS.md`
- `home/config.toml` -> `~/.codex/config.toml`에 merge
- `home/skills/` -> `~/.agents/skills/`

`~/.codex/rules/default.rules`는 Codex 승인 규칙 파일이므로 이 저장소가 덮어쓰지 않는다.

`~/.agents/skills/`는 다른 도구나 수동 설치 skill도 함께 쓸 수 있는 공유 경로다. 따라서 sync는 이 repo에 존재하는 skill 이름만 추가·갱신하고, 고아 검사도 그 디렉터리 내부로 한정한다. 다른 이름의 skill은 건드리지 않는다.

> **이전 `~/.codex/skills/` 사용자**: sync는 이 repo가 관리하는 것과 같은 이름의 legacy skill만 찾아 백업한 뒤 삭제 여부를 묻는다. Codex 소유의 `~/.codex/skills/.system/`과 다른 사용자 skill은 건드리지 않는다. 중복 로딩을 피하려면 새 경로 반영 후 legacy 사본을 정리하는 편이 좋다.

> **2026-06-23 이전에 sync한 머신**: 당시 함께 sync됐던 `~/.codex/rules/dev-tools/`가 잔류할 수 있다. Codex가 지시문으로 읽지 않아 무해하지만, `rm -rf ~/.codex/rules/dev-tools/`로 정리하면 깔끔하다.
