# 인프라 구축 체크리스트

> 갱신일: 2026-04-25  
> 목표: Proxmox + k3s + GPU + GitOps + vLLM 추론 서버

---

## Phase 1 — Proxmox GPU 패스스루
- [x] PVE-001 · IOMMU 활성화 (amd_iommu=on iommu=pt)
- [x] PVE-001 · vfio-pci 모듈 등록
- [x] PVE-001 · nouveau 블랙리스트
- [x] PVE-001 · RTX 3080 vfio-pci 바인딩 (10DE:2206, 10DE:1AEF)
- [x] PVE-001 · initramfs 업데이트
- [x] PVE-001 · 재부팅 후 `Kernel driver in use: vfio-pci` 확인

## Phase 2 — VM 100 기본 설정
- [x] PVE-002 · VM 100에 hostpci0 추가 (PCIe passthrough)
- [x] PVE-002 · VM 코어 1 → 4로 증설
- [x] PVE-002 · PVE 호스트 → VM SSH 키 설정
- [x] PVE-002 · VM sudo NOPASSWD 설정
- [x] PVE-002 · k3s kubeconfig 권한 설정 (write-kubeconfig-mode: "0644")

## Phase 3 — NVIDIA 드라이버 (VM 100)
- [x] GPU-001 · linux-headers, build-essential, dkms 설치
- [x] GPU-001 · nvidia-driver-580-open 설치
- [x] GPU-001 · 재부팅 후 nvidia-smi 확인 (Driver 580.126.09 / CUDA 13.0)
- [x] GPU-002 · NVIDIA Container Toolkit 설치

## Phase 4 — k3s 설치 (VM 100)
- [x] K8S-001 · k3s v1.34.6 설치 (traefik 비활성화)
- [x] K8S-001 · kubeconfig ~/.kube/config 복사
- [x] K8S-001 · 노드 Ready 확인

## Phase 5 — GitOps (GitHub + ArgoCD)
- [x] GITOPS-001 · GitHub SSH 키 생성 및 등록 (ksh@pve-github)
- [x] GITOPS-001 · infra 리포 생성 및 초기 구조 푸시
- [x] GITOPS-001 · ArgoCD stable 설치 (k3s)
- [x] GITOPS-001 · ArgoCD NodePort 30443 노출
- [x] GITOPS-001 · GitHub Deploy Key 생성 및 등록 (argocd@ubuntu-1)
- [x] GITOPS-001 · ArgoCD repo Secret 등록
- [x] GITOPS-002 · App-of-Apps 구조 (root → gpu-operator, kai-scheduler, vllm)
- [x] GITOPS-002 · GPU Operator v26.3.1 Synced ✓
- [x] GITOPS-002 · KAI Scheduler v0.5.4 Synced ✓ (OCI 래퍼 차트)

## Phase 6 — IaC 구조화
- [x] IaC-001 · Terraform 1.14.9 설치
- [x] IaC-001 · Proxmox API 토큰 생성 (terraform@pve!terraform)
- [x] IaC-001 · bpg/proxmox provider 설정
- [x] IaC-001 · VM 101 (worker-gpu) Terraform 코드 작성
- [x] IaC-002 · Ansible inventory (hosts.ini) 작성
- [x] IaC-002 · setup-nvidia.yml playbook
- [x] IaC-002 · setup-k3s.yml playbook
- [x] IaC-002 · setup-k3s-agent.yml playbook

## Phase 7 — GPU 워커 노드 + vLLM (진행 중)
- [x] PVE-003 · Terraform으로 VM 101 생성 (`terraform apply`) — 192.168.1.24
- [x] PVE-003 · GPU passthrough VM 100 → VM 101 이동 (RTX 3080 인식 확인)
- [x] PVE-003 · PCI Resource Mapping `rtx3080` 생성 (iommugroup=16)
- [x] PVE-003 · TerraformRole에 `Mapping.Use` 권한 추가
- [x] PVE-003 · root SSH 키 인증 설정 (Terraform SSH 작업용)
- [x] GPU-003 · VM 101 NVIDIA 드라이버 580-open 설치 (Ansible)
- [x] GPU-003 · GPU Operator가 worker-gpu 자동 감지 → nvidia.com/gpu:1 노출
- [x] K8S-002 · VM 101 k3s agent 조인 (Ansible)
- [x] K8S-002 · 멀티 노드 확인 (ubuntu-1: control-plane / worker-gpu: Ready)
- [ ] ML-001 · vLLM ArgoCD App Sync (Gemma 3 4B)
- [ ] ML-001 · 모델 로드 확인 (`/health` endpoint)
- [ ] ML-001 · OpenAI API 호환 테스트

## Backlog
- [ ] PVE-004 · Terraform으로 VM 100도 코드화 (현재는 수동 생성)
- [ ] K8S-003 · 워커 노드 추가 확장 (물리 머신)
- [ ] ML-002 · Gemma 3 12B INT4 (QAT) 테스트
- [ ] ML-002 · HuggingFace 토큰 k8s Secret으로 관리
- [ ] GITOPS-003 · KAI Scheduler 필요성 재검토 (추론 전용이라 불필요 가능)
- [ ] IaC-003 · Ansible Galaxy role 분리
