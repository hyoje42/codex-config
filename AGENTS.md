# Codex 설정 관리 저장소 — 작업 안내

`dev-ai-tools`의 submodule. 구조·스크립트·머신 종속 메커니즘 등 개요는 [README.md](./README.md)에 있다. 이 문서는 agent가 이 repo를 수정·관리할 때 지킬 규칙만 담는다.

경로 지도: `home/`만 `~/.codex/`로 sync · `local/`은 머신 종속 템플릿(`*.example`) · 실제 머신 값은 `~/.codex/config.toml`(repo가 읽지 않음).

## 작업 규칙

- **sync 게이트**: `~/.codex/` 반영(`codex-sync-to-home` 실행이든 수동 복사든)은 **사용자가 명시적으로 지시했을 때만**. 평소엔 `codex-diff-with-home`으로 차이만 확인해 공유한다.
- **sync 영역 경계**: `home/` 밖 파일을 sync 대상으로 옮기거나 그 반대를 하지 말 것.
- **머신 종속 값**: `local/`의 `*.example`만 커밋. 실제 값(`~/.codex/config.toml` 등)은 커밋 금지. config.toml은 **seed-if-absent**(없을 때만 seed, 있으면 보존)이며 merge가 아니다.
- **승인 규칙 보존**: `~/.codex/rules/default.rules`는 Codex 승인 규칙이라 이 repo가 덮어쓰지 않는다.
- **커밋 순서**: submodule에서 먼저 commit → 부모에서 포인터 commit.
- **메커니즘 무단 이식 금지**: claude-config의 settings merge 방식을 여기로(seed-if-absent를 그쪽으로) 옮기지 말 것.
- **skill 작성·이식**: 형식과 Claude→Codex 변환 규칙은 [skill-authoring.md](./skill-authoring.md) 참고.
