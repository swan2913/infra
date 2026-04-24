# GPU 도메인 에이전트 규칙

## 담당 범위
GPU 패스스루 설정, NVIDIA 드라이버, Container Toolkit, GPU 리소스 노출.

## 작업 원칙

- 드라이버 설치/업데이트 후 반드시 재부팅 필요
- `nvidia-driver-*-open` 시리즈 사용 (consumer GPU VM 내 오류 43 방지)
- VM 내 `nouveau` 모듈은 드라이버 충돌 유발 — 이미 blacklist 처리됨
- GPU Operator가 클러스터에 배포된 경우 `driver.enabled: false` 유지 (VM에 직접 설치했으므로)

## 상태 확인 명령어

```bash
# VM 내에서
nvidia-smi                           # GPU 상태
lsmod | grep nvidia                  # 모듈 로드 확인
nvidia-ctk --version                 # Container Toolkit 버전

# 클러스터에서
kubectl describe node | grep nvidia  # GPU 리소스 노출 확인
kubectl get pods -n gpu-operator     # GPU Operator 상태
```

## 파일 위치
- 드라이버 설치 문서: `docs/GPU/GPU-001-nvidia-driver-passthrough.md`
- GPU Operator 설정: `clusters/ubuntu-1/argocd-apps/gpu-operator.yaml`
