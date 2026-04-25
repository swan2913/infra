# ML-007 · ADR: DSPy 배포 위치

> 작성일: 2026-04-25  
> 상태: 채택

## 목적

DSPy로 Hermes Agent의 인프라 태스크 프롬프트를 자동 최적화한다.  
최적화 결과를 Hermes config.yaml에 반영해 명령 선택 정확도를 높인다.

## 선택지

### A. k8s Job / CronJob (Pod)

**단점**
- DSPy는 GPU가 필요 없음 — llama.cpp API를 HTTP로 호출할 뿐
- 지속 실행 서비스가 아니라 1회성 배치 작업
- 결과(최적화된 프롬프트)를 Pod 밖으로 꺼내는 과정 복잡 (ConfigMap, PVC 등)
- 최적화 주기가 짧지 않아 CronJob 오버헤드 불필요
- **채택하지 않음**

### B. PVE 호스트 직접 실행 ✅ 채택

**장점**
- Python 3.13 이미 설치됨
- llama.cpp API(`http://192.168.1.24:30800/v1`)에 직접 접근 가능
- 최적화 결과를 `/opt/hermes/data/config.yaml`에 바로 쓸 수 있음
- Hermes 재시작 한 번으로 즉시 반영
- 필요할 때 수동 실행 or `systemd timer`로 주기 실행 가능

**구조**
```
PVE 호스트
  /home/ksh/infra/dspy/
    optimize.py       ← DSPy 최적화 스크립트
    dataset.json      ← 인프라 태스크 예시 (20~30개)
    last_result.json  ← 최적화 결과 보존

  실행: python3 /home/ksh/infra/dspy/optimize.py
  결과: /opt/hermes/data/config.yaml 자동 갱신 → systemctl restart hermes
```

## 결정

**B 채택.** DSPy 최적화는 배치 작업이고 GPU가 필요 없으므로 PVE 호스트에서 직접 실행한다.
