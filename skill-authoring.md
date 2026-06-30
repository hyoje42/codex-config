# Skill 작성·이식 가이드 (Codex)

Codex skill은 `home/skills/<skill-name>/SKILL.md` 형식으로 둔다. 이 문서는 새 skill을 만들거나 Claude skill을 Codex로 옮길 때 참고한다.

## 형식

- frontmatter에는 최소 `name`, `description`을 둔다.
- skill이 쓰는 스크립트·참고 문서는 그 skill 디렉터리 안에 함께 둔다.

## Claude → Codex 이식 시 변환

Claude에서 가져온 rule/skill을 Codex로 옮길 때는 도구별 차이를 반드시 변환한다.

- 경로: `.claude` → `.codex`
- Claude 전역 rule(`home/rules/*.md`)은 Codex에선 `home/rules/`가 아니라 `home/AGENTS.md`의 섹션으로 넣는다 — Codex는 `~/.codex/rules/`를 지시문으로 로드하지 않고, 전역 지시문이 `AGENTS.md` 단일 파일이기 때문.
- Claude 전용 도구명(예: `TaskCreate`, `TaskList` 등)은 Codex 대응 기능으로 바꾸거나, 대응이 없으면 Codex sub-agent 방식 등으로 재작성한다.
- Claude 설정(예: `settings.json` 필드) 중 Codex에 대응이 없는 항목은 옮기지 않는다.

## 동기화 검증

두 도구의 skill이 서로 어긋나지 않는지는 부모 repo 루트의 `check-sync-status`로 기계 비교한다(rule은 도구별 위치가 달라 — claude `home/rules/` ↔ codex `home/AGENTS.md` — 비교 대상이 아니다). 변환 사유와 rule 정합성은 `docs/skill-sync-status.md`에 기록한다.
