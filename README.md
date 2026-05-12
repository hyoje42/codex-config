# Codex 설정 관리 저장소

Codex를 더 편하게 사용하기 위한 커스텀 skill, rule, 전역 지시문을 만들고 `~/.codex/`에 동기화하는 저장소.

## 구조

- `AGENTS.md` - Codex 전역 지시문으로 동기화할 내용
- `rules/` - 규칙 원문과 관리용 문서
- `skills/` - 커스텀 skill 정의 (`SKILL.md` 형식)
- `.codex/handoffs/` - 프로젝트 로컬 handoff 예시/기록
- `settings-notes.md` - Claude 설정 중 Codex에 그대로 적용할 수 없는 항목
- `_backup/` - `~/.codex` 동기화 전 백업

## 스크립트

- `codex-sync-to-home` - 이 repo의 `AGENTS.md`, `rules/`, `skills/`를 `~/.codex/`로 복사
- `codex-diff-with-home` - 이 repo와 `~/.codex/` 간 차이 확인

## 작업 흐름

1. 이 repo에서 `AGENTS.md`, `rules/`, `skills/` 수정
2. `./codex-diff-with-home`으로 차이 확인
3. `./codex-sync-to-home`으로 `~/.codex/`에 반영
4. 필요한 경우 이 관리 폴더를 별도 Git 저장소로 커밋

## Skill 작성 가이드

Codex skill은 `skills/<skill-name>/SKILL.md` 형식을 사용한다.

- frontmatter에는 최소 `name`, `description`을 둔다.
- 스크립트나 참고 문서는 skill 디렉터리 내부에 함께 둔다.
- Claude 전용 도구명이나 경로(`.claude`, `TeamCreate`, `TaskCreate`)는 Codex 도구와 경로로 바꾼다.

## 제외한 항목

- `claude/reference-skills/`는 submodule이라 복사하지 않았다.
- `claude/_backup/`은 Claude 홈 백업이라 Codex에는 새 `_backup/`만 만들었다.
- `claude/settings.json`은 Codex와 설정 형식이 달라 그대로 동기화하지 않는다. 세부 내용은 `settings-notes.md` 참고.

## 동기화 위치

- `AGENTS.md` -> `~/.codex/AGENTS.md`
- `skills/` -> `~/.codex/skills/`
- `rules/` -> `~/.codex/rules/dev-tools/`

`~/.codex/rules/default.rules`는 Codex 승인 규칙 파일이므로 이 저장소가 덮어쓰지 않는다.
