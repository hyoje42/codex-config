# Codex 설정 관리 저장소

Codex를 더 편하게 사용하기 위한 커스텀 skill, rule, 전역 지시문을 만들고 `~/.codex/`에 동기화하는 저장소.

## 구조

- `home/` — `~/.codex/`로 sync되는 영역. 폴더 구조가 `~/.codex/` 레이아웃을 그대로 미러링한다.
  - `home/AGENTS.md` — Codex 전역 지시문 (`~/.codex/AGENTS.md`로 sync). **이 파일은 sync payload이며, repo meta 문서가 아니다.**
  - `home/rules/dev-tools/` — 규칙 원문 (`~/.codex/rules/dev-tools/`로 sync)
  - `home/skills/` — 커스텀 skill 정의 (`SKILL.md` 형식)
- `local/` — **머신 종속 설정의 템플릿을 두는 곳 (sync 대상 아님).**
  - `local/config.toml.example` — `~/.codex/config.toml`의 커밋용 템플릿. sync가 config.toml이 없는 머신에 한해 이 파일로 seed한다(아래 참고).
- `settings-notes.md` — Claude 설정 중 Codex에 그대로 적용할 수 없는 항목 정리
- `skill-authoring.md` — skill 작성·이식(Claude→Codex 변환) 가이드
- `outdated/` — 퇴역한 skill·rule의 기록용 보관소. **sync 대상 아님.**
- `README.md`(이 문서) — 이 repo 설명. / `AGENTS.md`(= `CLAUDE.md`) — agent 작업 규칙. 둘 다 **sync 대상 아님.**
- `_backup/` — `~/.codex` 동기화 전 백업. **수정 금지.**

## 스크립트

- `codex-sync-to-home` — `home/` 내용을 `~/.codex/`로 복사한다. `~/.codex/config.toml`이 없는 머신에서는 `local/config.toml.example`로 한 번 seed한다(이미 있으면 건드리지 않음). **사용자가 명시적으로 지시했을 때만 실행한다.**
- `codex-diff-with-home` — `home/`과 `~/.codex/`의 차이 확인. config.toml은 머신 종속이라 직접 비교하지 않고, sync가 config.toml에 무엇을 할지(seed/보존)를 안내한다.

## 작업 흐름

1. 공통 설정은 `home/` 하위(`AGENTS.md`·`rules/`·`skills/`)에서 수정한다. 머신 종속 값은 `~/.codex/config.toml`에서 직접 다룬다.
2. `./codex-diff-with-home`으로 차이를 확인한 뒤 사용자에게 결과를 공유한다.
3. **사용자의 명시적 지시가 있을 때만** `./codex-sync-to-home`으로 `~/.codex/`에 반영한다(스크립트 대신 수동 복사 등으로 `~/.codex/`를 바꾸는 것도 동일하게 지시가 필요).
4. `git commit`으로 변경 이력을 남긴다(`local/`의 실제 머신 파일은 커밋되지 않는다).

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

**Claude(claude-config)와의 차이**: Claude는 공통 baseline(`home/settings.json`)과 머신 override(`local/settings.override.json`)를 sync마다 **deep-merge**해 `~/.claude/settings.json`에 쓴다. Codex는 config.toml이 거의 전부 머신 값이라 merge할 공통 baseline이 사실상 없으므로, **seed 후 직접 편집** 방식을 쓴다. 배치(`local/`·`.example`)·문서·스크립트 출력은 양쪽을 대칭으로 맞췄지만, 적용 메커니즘은 도구 특성에 맞게 다르다.

## 제외한 항목

- `claude-config/reference-skills/`는 submodule이라 복사하지 않았다.
- `claude-config/_backup/`은 Claude 홈 백업이라 Codex에는 새 `_backup/`만 만들었다.
- `claude-config/home/settings.json`은 Codex와 설정 형식이 달라 그대로 동기화하지 않는다. 세부 내용은 `settings-notes.md` 참고.

## 동기화 위치

`home/` 안의 경로가 그대로 `~/.codex/` 아래에 매핑된다.

- `home/AGENTS.md` -> `~/.codex/AGENTS.md`
- `home/skills/` -> `~/.codex/skills/`
- `home/rules/dev-tools/` -> `~/.codex/rules/dev-tools/`

`~/.codex/rules/default.rules`는 Codex 승인 규칙 파일이므로 이 저장소가 덮어쓰지 않는다.
