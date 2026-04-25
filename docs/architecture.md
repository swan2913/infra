# 인프라 아키텍처

> 갱신일: 2026-04-25

## 시스템 구성

```
[Proxmox Host 192.168.1.94]  (AMD Ryzen 5 5600X / 62GB RAM)
  │  Hermes Agent (systemd) · Terraform · Ansible
  │
  ├─ VM 100: ubuntu-1 (192.168.1.234)
  │     Ubuntu 24.04 / 4코어 / 4GB RAM / 64GB NVMe
  │     k3s v1.34 Control Plane · ArgoCD · kubeconfig
  │
  └─ VM 101: worker-gpu (192.168.1.24)
        Ubuntu 24.04 / 8코어 / 16GB RAM / 64GB NVMe
        RTX 3080 PCIe Passthrough (10GB VRAM, 250W limit)
        k3s Worker · NVIDIA Driver 580 · llama.cpp 추론 서버
```

## 네트워크

| 노드 | IP | 역할 |
|------|-----|------|
| PVE 호스트 | 192.168.1.94 | 하이퍼바이저 · Hermes Agent |
| VM 100 (ubuntu-1) | 192.168.1.234 | k3s Control Plane · ArgoCD |
| VM 101 (worker-gpu) | 192.168.1.24 | k3s Worker · GPU 워크로드 |

## 서비스 엔드포인트

| 서비스 | URL |
|--------|-----|
| PVE 웹UI | https://192.168.1.94:8006 |
| ArgoCD UI | https://192.168.1.234:30443 |
| llama.cpp API (외부) | http://192.168.1.24:30800/v1 |
| llama.cpp API (클러스터 내) | http://vllm.vllm.svc.cluster.local:8000/v1 |

## 접속

```bash
ssh vm100          # ubuntu-1 (Control Plane)
ssh worker-gpu     # VM 101 (GPU 워커)
ssh vm100 kubectl get nodes
```

## 스택 레이어

| 레이어 | 구성 요소 |
|--------|-----------|
| 하이퍼바이저 | Proxmox VE 9.1.1 (Debian 13) |
| IaC | Terraform (bpg/proxmox) + Ansible |
| 컨테이너 오케스트레이션 | k3s v1.34 (멀티 노드) |
| GitOps | ArgoCD (App-of-Apps) |
| GPU 스케줄링 | NVIDIA GPU Operator v26.3.1 |
| LLM 추론 | llama.cpp (Carnice-9b-Q6_K.gguf, 128K ctx) |
| 자율 에이전트 | Hermes (PVE 호스트 systemd, Discord 봇 인터페이스) |

## 아키텍처 원칙

- **Control Plane 분리**: VM 100은 k3s CP 전용. GPU/워크로드와 동일 VM에 두지 않는다 (ADR: K8S-001).
- **GPU 워커 분리**: RTX 3080은 VM 101(worker-gpu)에 패스스루. GPU 장애가 CP 장애로 전파되지 않는다.
- **GitOps 단일 원천**: 모든 앱 배포는 git push → ArgoCD 자동 반영. `kubectl apply` 직접 실행은 긴급 시에만.
- **IaC 강제**: VM 생성/변경은 Terraform, VM 내 설정은 Ansible. 수동 CLI 변경 후 코드 역반영 금지.

## 관련 문서

- GPU 패스스루: `docs/GPU/GPU-001-nvidia-driver-passthrough.md`
- Power Limit 최적화: `docs/GPU/GPU-002-power-limit-optimization.md`
- k3s 설치: `docs/K8S/K8S-001-k3s-install.md`
- ArgoCD 설치: `docs/GITOPS/GITOPS-001-argocd-setup.md`
- Terraform: `docs/IaC/IaC-001-terraform-proxmox.md`
- llama.cpp 전환: `docs/ML/ML-002-vllm-llamacpp-전환.md`
- Hermes Agent: `docs/ML/ML-003-hermes-agent-배포.md`
