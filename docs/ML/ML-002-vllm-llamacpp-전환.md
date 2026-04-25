# ML-002 · vLLM → llama.cpp 전환

> RTX 3080 10GB VRAM 한계로 vLLM(AWQ) 대신 llama.cpp(GGUF) 방식으로 전환  
> 상태: 완료 — llama.cpp Running (worker-gpu, 128K ctx)

## 전환 배경

### 문제: CUDA OOM

초기 계획은 vLLM + Gemma 3 4B (BF16) 또는 W8A16 AWQ 9B 모델이었으나, 실제 배포 시
RTX 3080 10GB VRAM에서 CUDA Out of Memory 에러가 발생했다.

| 시도 | 모델 | 방식 | 결과 |
|------|------|------|------|
| 1차 | google/gemma-3-4b-it | BF16 | OOM (vLLM overhead 포함 시 초과) |
| 2차 | Carnice-9b AWQ W8A16 | vLLM AWQ | OOM (9B W8A16 ~9GB + overhead) |
| 3차 | Carnice-9b-Q4_K_M.gguf | llama.cpp | **성공** (5.3GB, 여유 있음) |

### 해결: llama.cpp GGUF Q4_K_M

- GGUF Q4_K_M 양자화: 9B 파라미터 모델을 5.3GB로 압축
- llama.cpp는 vLLM보다 VRAM 오버헤드가 적음
- KV 캐시도 Q4_0으로 양자화해 VRAM 추가 절약

## 최종 구성

### 이미지

```
ghcr.io/ggml-org/llama.cpp:server-cuda
```

이전에는 `ggerganov/llama.cpp`를 사용했으나, 이미지 저장소가
`ghcr.io/ggml-org/llama.cpp`로 이전됨.

### 모델

| 항목 | 값 |
|------|-----|
| HuggingFace 리포 | `kai-os/Carnice-9b-GGUF` |
| 파일명 | `Carnice-9b-Q4_K_M.gguf` |
| 크기 | 5.3GB |
| 양자화 | Q4_K_M (4-bit, K-quant) |

### 서버 실행 인자

```
--model /models/Carnice-9b-Q4_K_M.gguf
--n-gpu-layers 999          # 모든 레이어 GPU 오프로드
--host 0.0.0.0
--port 8000
--ctx-size 131072           # 128K 컨텍스트
--parallel 2                # 동시 요청 2개
--cache-type-k q4_0         # KV 캐시 Q4_0 양자화
--cache-type-v q4_0
--flash-attn on             # Flash Attention 활성화
```

## 배포 구조

### initContainer: 모델 자동 다운로드

Pod 최초 기동 시 initContainer가 HuggingFace에서 GGUF 파일을 PVC에 다운로드한다.
이미 존재하면 스킵.

```yaml
initContainers:
  - name: download-model
    image: python:3.11-slim
    command:
      - sh
      - -c
      - |
        MODEL_PATH="/models/{{ .Values.model.file }}"
        if [ -f "$MODEL_PATH" ]; then
          echo "Model already exists, skipping download."
          exit 0
        fi
        pip install -q huggingface_hub && \
        hf download {{ .Values.model.repo }} {{ .Values.model.file }} \
          --local-dir /models
```

### enableServiceLinks: false

k8s가 자동으로 주입하는 서비스 디스커버리 환경변수 중 `VLLM_PORT`가 llama.cpp 서버
내부 변수와 충돌하는 문제가 있었다. `enableServiceLinks: false`로 해결.

```yaml
spec:
  enableServiceLinks: false
```

### Recreate 전략

GPU는 단일 리소스이므로 RollingUpdate 불가. 구 Pod 종료 후 신 Pod 기동.

```yaml
strategy:
  type: Recreate
```

## 파일 위치

| 파일 | 경로 |
|------|------|
| Helm values | `charts/vllm/values.yaml` |
| Deployment 템플릿 | `charts/vllm/templates/deployment.yaml` |
| Service 템플릿 | `charts/vllm/templates/service.yaml` |
| ArgoCD App | `clusters/ubuntu-1/argocd-apps/vllm.yaml` |

## 접속 정보

| 항목 | 값 |
|------|-----|
| 외부 엔드포인트 | `http://192.168.1.24:30800` |
| 클러스터 내부 | `http://vllm.vllm.svc.cluster.local:8000` |
| 헬스체크 | `GET /health` |
| 모델 목록 | `GET /v1/models` |
| 채팅 | `POST /v1/chat/completions` |

## 동작 확인

```bash
# Pod 상태
ssh vm100 kubectl get pods -n vllm

# 헬스체크
curl http://192.168.1.24:30800/health
# → {"status":"ok"}

# 추론 테스트 (OpenAI 호환)
curl http://192.168.1.24:30800/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Carnice-9b-Q4_K_M.gguf",
    "messages": [{"role": "user", "content": "안녕하세요!"}]
  }'
```

## vLLM vs llama.cpp 비교

| 항목 | vLLM | llama.cpp |
|------|------|-----------|
| VRAM 효율 | 낮음 (PagedAttention overhead) | 높음 |
| 동시 처리 | 높음 (PagedAttention) | 보통 (`--parallel`) |
| 지원 포맷 | HuggingFace safetensors, AWQ 등 | GGUF |
| OpenAI 호환 | ✅ | ✅ |
| 128K 컨텍스트 | 어려움 (VRAM) | ✅ (KV 양자화) |
| 홈랩 10GB GPU | 한계 있음 | 적합 |
