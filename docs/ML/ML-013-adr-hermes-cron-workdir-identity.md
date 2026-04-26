# ML-013 ADR: Hermes Cron 세션 정체성 — workdir 파라미터

**날짜**: 2026-04-26  
**상태**: 적용됨

---

## 문제

Hermes cron 잡이 Discord로 메시지를 전송할 때, 정체성이 "Vous Research에서 개발한 Hermes Agent입니다..."로 나왔다. config.yaml에 `agent.system_prompt`를 설정하고 SOUL.md를 배치해도 적용되지 않았다.

---

## 원인 분석

`cron/scheduler.py`에서 AIAgent를 생성할 때:

```python
skip_context_files=not bool(_job_workdir),
```

- `_job_workdir`는 cron 잡의 `workdir` 필드에서 온다.
- **workdir가 없으면** `skip_context_files=True` → SOUL.md·AGENTS.md 로드 안 됨
- SOUL.md가 없으면 `DEFAULT_AGENT_IDENTITY`("You are Hermes Agent, created by Nous Research...") 사용

`agent.system_prompt`(config.yaml)도 gateway 세션에서는 ephemeral prompt로 주입되지만, cron 스케줄러는 이 값을 AIAgent에 전달하지 않는다.

---

## 선택지

### A. 스케줄러 소스 패치
- `cron/scheduler.py`에서 `_cfg.get("agent", {}).get("system_prompt")`를 읽어 `ephemeral_system_prompt`로 전달
- `skip_context_files=False`로 강제 변경

**기각 이유**: hermes-agent 패키지 업데이트 시 패치 유실 위험. 부작용(cwd 기반 AGENTS.md 탐색) 예측 어려움.

### B. cron 잡 생성 시 `--workdir /opt/hermes/data` 지정 (채택)

```bash
HERMES_HOME=/opt/hermes/data hermes cron create \
  --workdir /opt/hermes/data \
  ...
```

workdir 지정 시 스케줄러 동작:
1. `_job_workdir` 설정 → `skip_context_files=False`
2. `TERMINAL_CWD=/opt/hermes/data` → `load_soul_md()` HERMES_HOME에서 로드
3. `build_context_files_prompt(cwd=TERMINAL_CWD)` → `/opt/hermes/data/AGENTS.md` 로드

**채택 이유**: 소스 수정 없음. `/opt/hermes/data/`에 SOUL.md·AGENTS.md가 있으므로(ExecStartPre가 복사) 정확히 원하는 파일을 로드한다.

---

## 구현

```bash
# cron 잡 생성 시 --workdir 필수
HERMES_HOME=/opt/hermes/data /opt/hermes-agent/.venv/bin/hermes cron create \
  --name "job-name" \
  --deliver "discord:1497321508379426897" \
  --workdir "/opt/hermes/data" \
  "0 9 * * *" \
  "프롬프트 내용"
```

## 검증

세션 파일 `sessions/session_cron_def22bf972b3_*.json`:
- **수정 전**: `system_prompt` = "You are Hermes Agent, an intelligent AI assistant created by Nous Research..."
- **수정 후**: `system_prompt` = "# Hermes — Infrastructure Agent Identity\n\nYou are **Hermes**..."

Discord DM 응답:
- **수정 전**: "저는 Hermes Agent입니다. Nous Research에서 개발한..."
- **수정 후**: "이름: Hermes / 모델: Carnice-9b (kai-os/Carnice-9b) / 실행 환경: Proxmox VE 호스트 - 네이티브 설치"

---

## 교훈

Hermes cron 잡에서 SOUL.md·AGENTS.md가 로드되려면 반드시 `--workdir`을 지정해야 한다. workdir 없이 생성된 잡은 기본 "Nous Research" 정체성을 사용한다. 이 규칙은 모든 cron 잡 생성 시 적용된다.
