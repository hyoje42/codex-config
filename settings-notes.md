# Claude settings.json 변환 메모

`claude/settings.json`은 Claude Code 전용 설정이라 Codex에 그대로 적용하지 않았다.

## Codex에 그대로 적용하지 않은 항목

- `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`
  - Claude 전용 실험 플래그다.
  - Codex에는 같은 `TeamCreate`/`TaskCreate` 기능이 없어서 `setup-team-agents` skill을 Codex sub-agent 방식으로 재작성했다.

- `env.CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING`
  - Claude 전용 환경 변수다.

- `env.MAX_THINKING_TOKENS`
  - Claude 전용 환경 변수다.
  - Codex의 reasoning effort는 `~/.codex/config.toml`의 모델/추론 설정으로 관리된다.

- `permissions.allow`, `permissions.deny`, `defaultMode`
  - Claude 권한 DSL이다.
  - Codex는 `~/.codex/rules/default.rules`, sandbox, approval 정책을 사용한다.
  - 기존 Codex 승인 규칙을 덮어쓰면 위험하므로 동기화 대상에서 제외했다.

- `skipDangerousModePermissionPrompt`, `skipAutoPermissionPrompt`
  - Claude 전용 프롬프트 설정이다.

## Codex에 반영한 방식

- 언어/응답/도구 사용 규칙은 `AGENTS.md`와 `rules/`에 반영했다.
- 커스텀 skill은 `skills/`에 반영했다.
- 전역 반영은 `./codex-sync-to-home`으로 수행한다.

## 수동 설정이 필요한 경우

Codex 모델, reasoning effort, project trust, plugin 활성화 같은 설정은 기존 `~/.codex/config.toml`을 직접 편집해서 관리한다. 이 저장소의 스크립트는 현재 `config.toml`을 덮어쓰지 않는다.
