# Codex 설정 관리 저장소

Codex를 더 편하게 사용하기 위한 커스텀 skill, rule, 전역 지시문을 만들고 `~/.codex/`에 동기화하는 저장소.

사람용 개요는 [README.md](./README.md)에 있다. 이 문서는 agent를 위한 안내다.

## 구조

- `home/` — `~/.codex/`로 그대로 sync되는 영역. 이 폴더 안의 구조는 `~/.codex/` 레이아웃을 미러링한다.
  - `home/AGENTS.md` — Codex 전역 지시문 (`~/.codex/AGENTS.md`로 sync). **이 파일은 sync payload이며, 본 meta 문서가 아니다.**
  - `home/rules/dev-tools/` — 규칙 원문 (`~/.codex/rules/dev-tools/`로 sync)
  - `home/skills/` — 커스텀 skill 정의 (`SKILL.md` 형식)
- `outdated/` — 퇴역한 skill·rule의 기록용 보관소. **sync 대상 아님.** 사유는 [outdated/README.md](./outdated/README.md) 참고.
- `AGENTS.md` (이 문서) — repo 자체를 다룰 때 참고하는 meta 문서. **sync 대상 아님.**
- `README.md` — 사람용 개요. 동일 정보를 narrative 톤으로.
- `settings-notes.md` — Claude 설정 중 Codex에 그대로 적용할 수 없는 항목 정리
- `_backup/` — `~/.codex` 동기화 전 백업. **수정 금지.**

## 스크립트

- `codex-sync-to-home` — `home/` 내용을 `~/.codex/`로 복사. **사용자가 명시적으로 지시했을 때만 실행할 것.**
- `codex-diff-with-home` — `home/`과 `~/.codex/` 간 차이 확인

## 작업 흐름

1. 이 repo의 `home/` 하위에서 `AGENTS.md`/`rules/`/`skills/` 수정
2. `./codex-diff-with-home`으로 차이 확인 후 사용자에게 결과 공유
3. **사용자의 명시적 지시가 있을 때만** `./codex-sync-to-home`으로 `~/.codex/`에 반영 (스크립트 대신 수동 복사 등으로 `~/.codex/`를 변경하는 것도 동일하게 지시가 필요)
4. Git commit으로 변경 이력 관리

## 주의사항

- `home/` 밖의 파일은 sync되지 않는다. 임의로 sync 영역 안팎으로 옮기지 말 것.
- `~/.codex/rules/default.rules`는 Codex 승인 규칙 파일이라 이 저장소가 덮어쓰지 않는다.
- Claude 설정에서 가져온 rule/skill을 Codex로 옮길 때는 도구명·경로 차이(`.claude` ↔ `.codex`, Claude 전용 도구명 등)를 반드시 변환한다.

## Skill 작성 가이드

Codex skill은 `home/skills/<skill-name>/SKILL.md` 형식을 사용한다.

- frontmatter에는 최소 `name`, `description`을 둔다.
- 스크립트나 참고 문서는 skill 디렉터리 내부에 함께 둔다.
- Claude 전용 도구명이나 경로(`.claude`, `TeamCreate`, `TaskCreate` 등)는 Codex 도구와 경로로 바꾼다. 세부 변환 규칙은 [README.md](./README.md)의 "Skill 작성 가이드"와 "제외한 항목" 절 참고.
