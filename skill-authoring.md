# Skill 작성·이식 가이드 (Codex)

Codex skill 원본은 `home/skills/<skill-name>/SKILL.md` 형식으로 두고, sync 시 공식 user skill 경로인 `~/.agents/skills/<skill-name>/`에 반영한다. 이 문서는 새 skill을 만들거나 Claude skill을 Codex로 옮길 때 참고한다.

공식 저장소의 bundled `skill-creator` 예시는 아직 `$CODEX_HOME/skills`를 기본값으로 안내하지만, 실제 [runtime loader](https://github.com/openai/codex/blob/main/codex-rs/core-skills/src/loader.rs)는 그 위치를 deprecated 호환 경로로 분류하고 `$HOME/.agents/skills`를 user skill 경로로 로드한다. 이 repo는 실행 동작의 기준인 loader를 따른다.

## 형식

- frontmatter에는 최소 `name`, `description`을 둔다.
- skill이 쓰는 스크립트·참고 문서는 그 skill 디렉터리 안에 함께 둔다.
- 사용자가 `$skill-name`으로 호출할 때만 실행해야 하는 skill은 `agents/openai.yaml`에 아래 정책을 둔다. `description` 문구만으로 자동 호출을 막지 않는다.

```yaml
policy:
  allow_implicit_invocation: false
```

## Claude → Codex 이식 시 변환

Claude에서 가져온 rule/skill을 Codex로 옮길 때는 도구별 차이를 반드시 변환한다.

- 경로: `.claude` → `.codex`
- skill 설치 경로: `~/.claude/skills/` → `~/.agents/skills/` (`$CODEX_HOME/skills`는 공식 loader가 호환용 deprecated 경로로만 유지)
- Claude 전역 rule(`home/rules/*.md`)은 Codex에선 `home/rules/`가 아니라 `home/AGENTS.md`의 섹션으로 넣는다 — Codex는 `~/.codex/rules/`를 지시문으로 로드하지 않고, 전역 지시문이 `AGENTS.md` 단일 파일이기 때문.
- Claude 전용 도구명(예: `TaskCreate`, `TaskList` 등)은 Codex 대응 기능으로 바꾸거나, 대응이 없으면 Codex sub-agent 방식 등으로 재작성한다.
- Claude의 `disable-model-invocation: true`는 Codex `SKILL.md`에 복사하지 않고, skill-local `agents/openai.yaml`의 `policy.allow_implicit_invocation: false`로 변환한다.
- Claude 설정(예: `settings.json` 필드) 중 Codex에 대응이 없는 항목은 옮기지 않는다.
