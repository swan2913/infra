# ML-012 ADR: Hermes 크론 잡 → Host Systemd 타이머 이전

**날짜**: 2026-04-26  
**상태**: 적용됨

---

## 문제

Hermes의 내장 크론 스케줄러로 `dspy-optimize`, `dspy-remind`, `hermes-canary` 세 잡을 등록했으나, **LLM-in-LLM** 문제가 발생했다:

1. Hermes 크론 스케줄러가 잡 발화 → LLM에 프롬프트 전달
2. LLM이 Python 스크립트 실행 tool call 생성
3. 해당 스크립트(cron_optimize.py, hermes-canary.py) 내부에서 다시 LLM API 호출
4. Carnice-9b(thinking model)의 긴 추론 토큰 + 이중 호출 → max_tokens 초과
5. `finish_reason=length` → truncated tool call → 재시도 루프
6. GPU 97% 고착, Discord 알림 미전달

---

## 선택지

### A. Hermes 크론 유지 + 단순 메시지만 등록
- LLM API를 호출하지 않는 단순 작업만 크론에 등록
- DSPy/캐너리는 다른 방법으로 처리

**기각 이유**: Hermes 크론이 모든 잡을 LLM 경유로 처리하는 구조라, 단순 메시지도 max_tokens 문제가 발생함 (실제로 claude-notify 잡들도 실패했음).

### B. Host Systemd 타이머 (채택)
- 세 잡 모두 Hermes 크론에서 제거
- PVE 호스트 systemd 타이머로 이전
- 스크립트 직접 실행 → 결과를 Discord Bot API로 직접 전달

**채택 이유**: LLM 개입 없이 확실하게 실행. systemd 타이머는 Persistent=true 로 누락 없음. Discord 전달도 Bot API 직접 호출로 신뢰성 보장.

---

## 구현

```
hermes-canary.timer      → 09:00 KST (00:00 UTC)  run-hermes-canary.sh
hermes-dspy-optimize.timer → 12:00 KST (03:00 UTC)  run-dspy-optimize.sh
hermes-dspy-remind.timer  → 18:00 KST (09:00 UTC)  run-dspy-remind.sh
```

각 래퍼 스크립트는 Python 직접 실행 후 `hermes-notify`로 Discord 전달.

---

## 교훈

Hermes의 크론 스케줄러는 "에이전트에게 작업을 지시"하는 용도로 설계됐다. 그 작업이 다시 LLM을 호출하면 루프가 생긴다. LLM 추론을 포함하는 작업(DSPy 최적화, 캐너리 테스트)은 LLM 외부에서 직접 실행해야 한다.

Hermes 크론은 "LLM이 판단해서 실행해야 하는 작업"에만 적합하다. 스크립트 직접 실행은 systemd/crontab이 더 적합하다.
