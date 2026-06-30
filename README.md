# Codex 설정 관리 저장소

Codex를 더 편하게 사용하기 위한 커스텀 skill과 전역 지시문(AGENTS.md)을 만들고 `~/.codex/`에 동기화하는 저장소.

## 구조

- `home/` — `~/.codex/`로 sync되는 영역. 폴더 구조가 `~/.codex/` 레이아웃을 그대로 미러링한다.
  - `home/AGENTS.md` — Codex 전역 지시문 (`~/.codex/AGENTS.md`로 sync). **Codex가 로드하는 전역 규칙은 이 단일 파일이다**(`~/.codex/rules/`는 지시문으로 로드되지 않음). 이 파일은 sync payload이며, repo meta 문서가 아니다.
  - `home/skills/` — 커스텀 skill 정의 (`SKILL.md` 형식)
- `local/` — **머신 종속 설정의 템플릿을 두는 곳 (sync 대상 아님).** 루트 `.gitignore`가 `local/*`를 무시하고 `*.example` 템플릿만 추적한다. 실제 머신 값 파일(`config.toml`·`codex-proxy-wrapper.sh` 등)은 커밋되지 않는다.
  - `local/config.toml.example` — `~/.codex/config.toml`의 커밋용 템플릿. sync가 config.toml이 없는 머신에 한해 이 파일로 seed한다(아래 참고).
  - `local/codex-proxy-wrapper.sh.example` — 프록시 환경 로그인용 `~/.bashrc` codex 래퍼 템플릿. 실제 값은 `local/codex-proxy-wrapper.sh`(gitignore됨)에 채우고, sync가 `~/.bashrc`에 설치한다(아래 참고).
- `skill-authoring.md` — skill 작성·이식 가이드
- `outdated/` — 퇴역한 skill·rule의 기록용 보관소. **sync 대상 아님.**
- `README.md`(이 문서) — 이 repo 설명. / `AGENTS.md`(= `CLAUDE.md`) — agent 작업 규칙. 둘 다 **sync 대상 아님.**
- `_backup/` — `~/.codex` 동기화 전 백업. **수정 금지.**

## 스크립트

- `codex-sync-to-home` — `home/` 내용을 `~/.codex/`로 복사한다. `~/.codex/config.toml`이 없는 머신에서는 `local/config.toml.example`로 한 번 seed한다(이미 있으면 건드리지 않음). 또한 `local/codex-proxy-wrapper.sh`(실제 값)가 있고 `~/.bashrc`에 래퍼가 아직 없으면 한 번 설치한다(아래 참고). **사용자가 명시적으로 지시했을 때만 실행한다.**
- `codex-diff-with-home` — `home/`과 `~/.codex/`의 차이 확인. config.toml·codex 래퍼는 머신 종속이라 직접 비교하지 않고, sync가 각각에 무엇을 할지(seed/설치/보존)를 안내한다.

## 작업 흐름

1. 공통 설정은 `home/`(`AGENTS.md`·`skills/`)에서, 머신 종속 값은 `~/.codex/config.toml`·`local/`에서 수정한다.
2. `./codex-diff-with-home`으로 차이를 확인한다.
3. 필요할 때 `./codex-sync-to-home`으로 `~/.codex/`에 반영한다.
4. `git commit`으로 변경 이력을 남긴다(`local/`의 실제 머신 값은 커밋되지 않는다).

## 머신 종속 설정 (config.toml seed)

Codex의 모델·reasoning effort·project trust 같은 값은 **머신마다 달라** git에 올리지 않는다. 이 값들은 `~/.codex/config.toml`에 들어가는데, config.toml은 **sync 대상이 아니다**(거의 전부가 머신 종속 값이라 공통 baseline을 둘 의미가 없다).

대신 **seed-if-absent** 방식으로 다룬다.

**셋업**

1. 새 머신에 `~/.codex/config.toml`이 없으면, `./codex-sync-to-home`이 `local/config.toml.example`을 한 번 복사해 seed한다.
2. 이후 `~/.codex/config.toml`을 직접 열어 model·reasoning effort·project trust 등을 채워 넣는다.

**동작**

- `~/.codex/config.toml`이 **없을 때만** `local/config.toml.example`로 seed한다. **이미 있으면 절대 덮어쓰지 않는다**(직접 편집한 값을 보존).
- `codex-diff-with-home`은 config.toml을 직접 diff하지 않고, "없음 → seed 예정" / "있음 → 건드리지 않음"을 `ⓘ`로 안내한다(= sync하면 config.toml에 무엇이 일어날지).

> 실제 머신 값을 채운 파일은 `~/.codex/config.toml`에 두고 절대 커밋하지 말 것. `local/`에 실수로 실제 `config.toml`을 두더라도 `.gitignore`가 막는다(`.example` 템플릿만 추적됨).

## 머신 종속 설정 (프록시·CA 로그인 래퍼)

프록시 환경(기업 프록시, TLS 검사 방화벽 등)에서는 `codex login`이 토큰 교환 단계에서 실패할 수 있다. 프록시가 TLS를 가로채 자체 CA로 재서명하는데, codex 본체(로그인/OAuth/API)가 그 CA를 신뢰하지 못하기 때문이다. 이 프록시·CA 설정은 `config.toml`이 아니라 codex **실행 시점의 env**(`HTTPS_PROXY`·`CODEX_CA_CERTIFICATE` 등)로만 잡히므로 `~/.bashrc`의 `codex()` 래퍼로 주입한다. config.toml과 달리 실제 값이 `~/.bashrc`에 들어가야 하므로, **실제 값 파일을 `local/`에 두고 sync가 `~/.bashrc`에 append**한다.

- **셋업**: `local/codex-proxy-wrapper.sh.example` → `local/codex-proxy-wrapper.sh`로 복사(루트 `.gitignore`로 추적 안 됨) → placeholder(프록시 주소·CA 경로 등)를 이 환경의 실제 값으로 채움 → `./codex-sync-to-home` → `source ~/.bashrc`.
- **동작**: `~/.bashrc`에 래퍼 마커가 이미 있으면 보존 / 실제 파일이 없으면 아무것도 안 함(`.example`만으론 설치 안 함) / placeholder가 남아 있으면 설치 보류. `codex-diff-with-home`이 이 판정을 미리 안내한다.

## 동기화 위치

`home/` 안의 경로가 그대로 `~/.codex/` 아래에 매핑된다.

- `home/AGENTS.md` -> `~/.codex/AGENTS.md`
- `home/skills/` -> `~/.codex/skills/`

`~/.codex/rules/default.rules`는 Codex 승인 규칙 파일이므로 이 저장소가 덮어쓰지 않는다.

> **2026-06-23 이전에 sync한 머신**: 당시 함께 sync됐던 `~/.codex/rules/dev-tools/`가 잔류할 수 있다. Codex가 지시문으로 읽지 않아 무해하지만, `rm -rf ~/.codex/rules/dev-tools/`로 정리하면 깔끔하다.
