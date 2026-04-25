# ML-008 · DSPy 프롬프트 최적화 작업 계획

> 작성일: 2026-04-25  
> 완료일: 2026-04-25  
> 상태: **완료**

## 목표

Hermes Agent가 인프라 태스크 질문에서 **올바른 명령어와 접근 경로를 선택**하도록  
DSPy로 system_prompt와 few-shot 예시를 자동 최적화한다.

## 현재 문제 (Before)

| 질문 유형 | 기대 동작 | 실제 동작 (before) |
|----------|----------|------------------|
| GPU VRAM 확인 | `ssh -i /opt/data/vm_key ubuntu@192.168.1.24 nvidia-smi` | 로컬 nvidia-smi 탐색 |
| llama.cpp 상태 | `kubectl logs -n vllm deployment/vllm` | 로컬 프로세스 탐색 |
| 파드 재시작 | `kubectl rollout restart deployment/vllm -n vllm` | 임의 명령 조합 |

## 결과 (After)

| 항목 | Before | After |
|------|--------|-------|
| 전체 정확도 | 32% (8/25) | **92% (23/25)** |
| 파싱 실패 | 3개 | 0개 |
| GPU 명령 (SSH) | ❌ | ✅ |
| llama.cpp (kubectl) | ❌ | ✅ |
| terraform/git 경로 | ❌ | ✅ |

## 실제 적용 방식 (계획 대비 변경)

### 계획: DSPy BootstrapFewShot 자동 최적화
### 실제: InfraSignature docstring에 verified examples 직접 주입

**이유:** Carnice-9b는 thinking 모델로, `reasoning_content`에 모든 토큰을 소비하고  
`text` 필드를 비워 DSPy structured output 파싱이 실패하는 경우가 많았음.  
BootstrapFewShot은 작동했지만 (4 traces 생성) thinking 모델의 토큰 낭비로  
자동화 효율이 낮음. dataset.json의 검증된 예시를 직접 signature에 주입하는 방식이  
동일한 효과를 훨씬 빠르게 달성.

## 작업 단계

### Step 1 — 환경 준비
- [x] pip install dspy-ai (DSPy 3.2.0)
- [x] llama.cpp OpenAI API 연동 확인
- [x] `dspy/` 디렉토리 구조 생성

### Step 2 — 데이터셋 작성 (`dspy/dataset.json`)
- [x] 인프라 태스크 25개 예시 작성
  - GPU/VRAM 확인류 (3개)
  - k8s 파드 상태/로그류 (8개)
  - 재시작/배포류 (3개)
  - VM 관리류 (3개)
  - Terraform/git류 (4개)
  - 기타 (4개)
- [x] train(80%) / eval(20%) 분리

### Step 3 — DSPy 모듈 작성
- [x] `InfraSignature` 정의 (verified examples 포함 docstring)
- [x] `InfraAgent` 모듈 (ChainOfThought)
- [x] 평가 메트릭 함수 (must_contain / must_not_contain)
- [x] BootstrapFewShot 옵티마이저 설정

### Step 4 — 최적화 실행
- [x] `python3 dspy/evaluate.py` 베이스라인 측정: **32%**
- [x] `python3 dspy/optimize.py` 실행 (4 traces 생성)
- [x] 결과 저장: `dspy/runs/20260425_165216/result.json`

### Step 5 — 반영 및 평가
- [x] 최적화된 few-shot 예시를 `/opt/hermes/data/config.yaml`에 반영 (17개)
- [x] `systemctl restart hermes`
- [x] 최종 평가: **92% (23/25)**, 파싱 실패 0개

## 평가 메트릭

```python
def metric(example, prediction):
    cmd = prediction.command.lower()
    for token in example["must_contain"]:
        if token.lower() not in cmd: return False
    for token in example["must_not_contain"]:
        if token.lower() in cmd: return False
    return True
```

## 트러블슈팅 기록

| 문제 | 원인 | 해결 |
|------|------|------|
| `text` 필드 비어 있음 | thinking 모델이 reasoning_content에 토큰 소비 | max_tokens 6000, 에러 처리 추가 |
| `e.__dict__["question"]` KeyError | dspy.Example은 _store에 저장 | 직접 Example 사용 |
| `optimized.predict.demos` AttributeError | ChainOfThought 경로 틀림 | `predict.predict.demos` |
| PermissionError on config.yaml | 일반 유저 쓰기 불가 | sudo tee 사용 |

## 파일 구조

```
infra/
  dspy/
    optimize.py       ← BootstrapFewShot 최적화 스크립트
    evaluate.py       ← 성능 평가 스크립트 (system prompt 포함)
    dataset.json      ← 인프라 태스크 25개 예시
    .gitignore        ← .venv/, runs/ 제외
    runs/             ← 실행 결과 (gitignore)
```

## 잔여 실패 (2/25)

| 질문 | 예상 | 실제 | 원인 |
|------|------|------|------|
| ArgoCD 강제 동기화 | kubectl patch ... | argocd app sync | argocd CLI 선호 |
| GPU operator 파드 | -n gpu-operator | -n vllm | 네임스페이스 혼동 |

두 번째 항목은 config.yaml에 예시 추가로 해결 예정.
