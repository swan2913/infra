# ML 도메인 에이전트 규칙

## 담당 범위
vLLM 추론 서버, 모델 관리, HuggingFace 연동.

## 작업 원칙

- 모델 변경은 `charts/vllm/values.yaml` 수정 → git push → ArgoCD 반영
- HuggingFace 토큰은 k8s Secret으로 관리 (git 금지)
- 모델 로드 시간 약 3-5분 — Pod Running 후 `/health` 로 확인
- VRAM 초과 시 Pod CrashLoopBackOff 발생 → 더 작은 모델 또는 양자화 사용

## RTX 3080 (10GB) 모델 선택 기준

| 모델 | 방식 | VRAM | 비고 |
|------|------|------|------|
| gemma-3-4b-it | BF16 | ~8GB | 기본 선택 |
| gemma-3-12b-it-qat | INT4 | ~7GB | 성능 우선 |
| gemma-3-27b-it | BF16 | 54GB | 불가 |

## 상태 확인

```bash
ssh vm100 kubectl get pods -n vllm
ssh vm100 kubectl logs -n vllm deploy/vllm -f

# 추론 테스트
curl http://<워커IP>:30800/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"google/gemma-3-4b-it","messages":[{"role":"user","content":"test"}]}'
```

## 파일 위치
- Helm 차트: `charts/vllm/`
- ArgoCD App: `clusters/ubuntu-1/argocd-apps/vllm.yaml`
- vLLM 문서: `docs/ML/ML-001-vllm-gemma.md`
