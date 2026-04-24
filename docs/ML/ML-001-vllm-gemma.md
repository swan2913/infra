# ML-001 · vLLM 추론 서버 (Gemma 모델)

> vLLM + Gemma 3 / k8s Pod 형태로 GPU 워커 노드에 배포  
> 상태: 준비 완료 (워커 노드 추가 후 Sync 예정)

## 모델 선택 기준 (RTX 3080 10GB VRAM)

| 모델 | VRAM | 비고 |
|------|------|------|
| google/gemma-3-4b-it | ~8GB (BF16) | ✅ 기본 선택, 여유 있음 |
| google/gemma-3-12b-it-qat | ~7GB (INT4) | ✅ 더 큰 모델, 양자화 |
| google/gemma-3-27b-it | 54GB (BF16) | ❌ VRAM 부족 |

## vLLM vs llama.cpp 선택 이유

**vLLM 선택:**
- PagedAttention으로 동시 요청 처리 효율 높음
- OpenAI API 호환 (`/v1/chat/completions`)
- k8s 환경에 자연스럽게 통합
- AWQ/GPTQ/QAT 양자화 모델 지원

## ArgoCD 배포 구조

```
charts/vllm/
├── Chart.yaml
├── values.yaml          ← 모델 변경 시 여기만 수정
└── templates/
    ├── deployment.yaml  ← GPU nodeSelector, PVC 마운트
    └── service.yaml     ← NodePort 30800
```

## 모델 변경 방법

```bash
# values.yaml 수정
vim ~/infra/charts/vllm/values.yaml
# model: "google/gemma-3-12b-it-qat"

git add -A && git commit -m "feat: switch to gemma-3-12b-it-qat" && git push
# → ArgoCD 자동 반영
```

## HuggingFace 토큰 설정 (Gated 모델용)

Gemma 모델은 HuggingFace 라이선스 동의 필요.

```bash
# HuggingFace 토큰을 k8s Secret으로 관리
kubectl create secret generic hf-token \
  --namespace vllm \
  --from-literal=token="hf_xxxxxxxxxxxx"
```

`deployment.yaml` 에 환경변수 추가:
```yaml
env:
  - name: HUGGING_FACE_HUB_TOKEN
    valueFrom:
      secretKeyRef:
        name: hf-token
        key: token
```

## 배포 후 확인

```bash
# Pod 상태 (모델 로드 약 3-5분 소요)
kubectl get pods -n vllm -w

# 헬스체크
curl http://192.168.1.XXX:30800/health
# → {"status":"ok"}

# 추론 테스트 (OpenAI 호환)
curl http://192.168.1.XXX:30800/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "google/gemma-3-4b-it",
    "messages": [{"role": "user", "content": "안녕하세요!"}]
  }'
```

## 접속 정보

| 항목 | 값 |
|------|-----|
| API 엔드포인트 | `http://<워커노드IP>:30800` |
| 헬스체크 | `GET /health` |
| 모델 목록 | `GET /v1/models` |
| 채팅 | `POST /v1/chat/completions` |
