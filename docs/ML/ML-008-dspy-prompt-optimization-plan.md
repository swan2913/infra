# ML-008 · DSPy 프롬프트 최적화 작업 계획

> 작성일: 2026-04-25  
> 상태: 진행 예정

## 목표

Hermes Agent가 인프라 태스크 질문에서 **올바른 명령어와 접근 경로를 선택**하도록  
DSPy로 system_prompt와 few-shot 예시를 자동 최적화한다.

## 현재 문제

| 질문 유형 | 기대 동작 | 실제 동작 (before) |
|----------|----------|------------------|
| GPU VRAM 확인 | `ssh -i /opt/data/vm_key ubuntu@192.168.1.24 nvidia-smi` | 로컬 nvidia-smi 탐색 |
| llama.cpp 상태 | `kubectl logs -n vllm deployment/vllm` | 로컬 프로세스 탐색 |
| 파드 재시작 | `kubectl rollout restart deployment/vllm -n vllm` | 임의 명령 조합 |

수작업 system_prompt 보강 후 부분 개선됐으나 일관성 부족.

## DSPy 최적화 접근

```
데이터셋 (examples.json)
  → DSPy MIPROv2 Optimizer
  → 최적화된 system_prompt + few-shot 예시
  → /opt/hermes/data/config.yaml 반영
  → systemctl restart hermes
  → 성능 비교 평가
```

### 사용할 DSPy 컴포넌트

- **Signature**: `InfraQuestion → TerminalCommand + Explanation`
- **Module**: `dspy.ChainOfThought(InfraSignature)`
- **Optimizer**: `MIPROv2` (소규모 데이터셋에 적합) 또는 `BootstrapFewShot`
- **Metric**: 응답에 올바른 명령어 패턴 포함 여부 (문자열 매칭 + LLM judge)

## 작업 단계

### Step 1 — 환경 준비
- [ ] pip install dspy-ai
- [ ] llama.cpp OpenAI API 연동 확인 (`dspy.LM("openai/...")`)
- [ ] `dspy/` 디렉토리 구조 생성

### Step 2 — 데이터셋 작성 (`dspy/dataset.json`)
- [ ] 인프라 태스크 20~30개 예시 작성
  - GPU/VRAM 확인류 (5개)
  - k8s 파드 상태 확인류 (5개)
  - 로그 확인류 (5개)
  - 재시작/배포류 (5개)
  - Terraform/Ansible류 (5개)
- [ ] train(80%) / eval(20%) 분리

### Step 3 — DSPy 모듈 작성 (`dspy/optimize.py`)
- [ ] `InfraSignature` 정의
- [ ] `InfraAgent` 모듈 (ChainOfThought)
- [ ] 평가 메트릭 함수 작성
- [ ] MIPROv2 옵티마이저 설정

### Step 4 — 최적화 실행
- [ ] `python3 dspy/optimize.py` 실행 (예상 소요: 30~60분, ~100 LLM 호출)
- [ ] 최적화 결과 검토
- [ ] `last_result.json` 저장

### Step 5 — 반영 및 평가
- [ ] 최적화된 프롬프트를 `/opt/hermes/data/config.yaml`에 반영
- [ ] `systemctl restart hermes`
- [ ] before/after 동일 질문으로 성능 비교
- [ ] 문서화 (ML-008 결과 업데이트)

## 평가 메트릭 설계

```python
def metric(example, prediction):
    response = prediction.command.lower()
    
    # 서비스 위치 정확도
    if "gpu" in example.question or "vram" in example.question:
        return "ssh" in response and "nvidia-smi" in response
    
    if "llama" in example.question or "log" in example.question:
        return "kubectl logs" in response and "vllm" in response
    
    if "재시작" in example.question or "restart" in example.question:
        return "kubectl rollout restart" in response
    
    if "terraform" in example.question:
        return "terraform" in response and "/infra" in response
    
    return False
```

## 예상 효과

| 항목 | 현재 | 목표 |
|------|------|------|
| 서비스 위치 정확도 | ~60% | >90% |
| 올바른 명령 선택 | ~50% | >85% |
| 불필요한 로컬 탐색 | 빈번 | 없음 |

## 파일 구조

```
infra/
  dspy/
    optimize.py       ← 메인 최적화 스크립트
    dataset.json      ← 인프라 태스크 데이터셋
    evaluate.py       ← 성능 평가 스크립트
    last_result.json  ← 최적화 결과 (gitignore)
```

## 주의사항

- 최적화 중 llama.cpp에 ~100회 API 호출 → 약 30~60분 소요
- 최적화 완료 전까지 Hermes 응답 속도에 영향 없음 (별도 프로세스)
- 결과 반영 시 Hermes 재시작 필요 (~10초 다운타임)
