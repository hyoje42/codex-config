# Codex Global Instructions

이 파일은 `codex-sync-to-home`으로 `~/.codex/AGENTS.md`에 동기화하기 위한 전역 지시문이다.

## Response Format

- 파일을 수정하기 전에는 무엇을 왜 바꾸는지 짧게 설명한다.
- 코드나 파일을 언급할 때는 가능한 한 클릭 가능한 절대 경로 markdown 링크를 사용한다.
- 사용자의 선호 언어가 있으면 그 언어로 답한다. 코드 식별자와 기술 용어는 원문을 유지해도 된다.
- 논리적으로 묶이는 변경은 한 번에 제안하거나 적용한다.

## Tool Usage

- 파일 관련 명령은 워크스페이스 루트 기준 상대 경로를 먼저 사용한다.
- 검색은 `rg` 또는 `rg --files`를 우선 사용한다.
- Python 명령을 실행할 때 워크스페이스 루트에 `.venv`가 있으면 먼저 활성화한다.
- 민감 정보로 보이는 파일(`.env`, 개인 키, credential, token, kube/aws/docker 설정 등)은 필요 없으면 읽거나 검색하지 않는다.

## Python

1. 워크스페이스 루트에 `.venv`가 있는지 확인한다.
2. 있으면 `source .venv/bin/activate && <python_command>` 형태로 실행한다.
3. 없으면 Python 명령을 직접 실행한다.

## Skills

이 저장소의 `skills/` 아래 skill은 `codex-sync-to-home` 실행 후 `~/.codex/skills/`에서 사용할 수 있다.

현재 포함된 skill:

- `git-commit-message`
- `handoff`
- `load-handoff`
- `make-plan`
- `review-pr`
- `setup-team-agents`
