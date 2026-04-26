# 인프라 구축 체크리스트

> 갱신일: 2026-04-26  
> 목표: Proxmox + k3s + GPU + GitOps + llama.cpp 추론 서버 + Hermes 자율 에이전트

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
- [x] IaC-002 · setup-nvidia-powerlimit.yml playbook (250W, systemd 영구 적용)
- [x] IaC-002 · setup-k3s.yml playbook
- [x] IaC-002 · setup-k3s-agent.yml playbook

## Phase 7 — GPU 워커 노드 + llama.cpp 추론 서버
- [x] PVE-003 · Terraform으로 VM 101 생성 (`terraform apply`) — 192.168.1.24
- [x] PVE-003 · GPU passthrough VM 100 → VM 101 이동 (RTX 3080 인식 확인)
- [x] PVE-003 · PCI Resource Mapping `rtx3080` 생성 (iommugroup=16)
- [x] PVE-003 · TerraformRole에 `Mapping.Use` 권한 추가
- [x] PVE-003 · root SSH 키 인증 설정 (Terraform SSH 작업용)
- [x] GPU-003 · VM 101 NVIDIA 드라이버 580-open 설치 (Ansible)
- [x] GPU-003 · GPU Operator가 worker-gpu 자동 감지 → nvidia.com/gpu:1 노출
- [x] K8S-002 · VM 101 k3s agent 조인 (Ansible)
- [x] K8S-002 · 멀티 노드 확인 (ubuntu-1: control-plane / worker-gpu: Ready)
- [x] GPU-002 · RTX 3080 Power Limit 최적화 — 250W (실측: 성능 93%, 전력 78%, W/tok 최저)
- [x] GPU-003 · Power Limit 미적용 인시던트 대응 — nvidia-powerlimit.service 실제 설치 (2026-04-26, ADR: GPU-003)
- [x] ML-001 · vLLM → llama.cpp 전환 (CUDA OOM으로 Gemma AWQ 포기)
- [x] ML-001 · Carnice-9b-Q4_K_M.gguf 모델 (5.3GB) 선택
- [x] ML-001 · llama.cpp ArgoCD App Sync — Running (worker-gpu)
- [x] ML-001 · 128K ctx, Q4_0 KV 캐시, Flash Attention 적용
- [x] ML-001 · `/health` endpoint 확인 ✓
- [x] ML-001 · OpenAI API 호환 (`/v1/chat/completions`) 테스트 ✓
- [x] ML-002 · vLLM → llama.cpp 전환 기록 문서화 (ML-002)
- [x] ML-004 · Carnice-9b Q4_K_M → Q6_K 업그레이드 (VRAM 분석 기반, perplexity -34%)
- [x] ML-005 · 모델 선택 및 VRAM 최적화 리서치 (컨텍스트/양자화/spec decoding/parallel 분석)

## Phase 8 — Hermes Agent (자율 인프라 에이전트)
- [x] ML-003 · Hermes Agent k8s Deployment 작성 (namespace: hermes)
- [x] ML-003 · Discord 봇 연결, GitHub 연결, Discord Privileged Gateway Intents 활성화
- [x] ML-003 · Hermes Agent 1/1 Running — Discord 연결 정상 ✓
- [x] ML-003 · Hermes config system_prompt에 에이전트 identity 주입 (모델 자기인식 hallucination 방지)
- [x] ML-005 · Hermes k8s → PVE 호스트 systemd 마이그레이션 (인프라 전자동화 목적)
- [x] ML-005 · docker --network=host + host 바이너리 마운트 (pveum, qm, kubectl, terraform 접근)
- [x] ML-005 · /etc/systemd/system/hermes.service 등록, 부팅 자동 시작 ✓
- [x] IaC-003 · Proxmox API 토큰 노출 → filter-branch 히스토리 정리 + 토큰 재발급 (IaC-003)
- [x] K8S-001 · Control plane 분리 원칙 확정 (ADR: VM 100 전용 유지)

## Phase 9 — Hermes Agent 안정화 (2026-04-26)
- [x] ML-011 · Hermes Docker → 네이티브 설치 전환 (qm/systemctl/docker 직접 접근)
- [x] ML-012 · LLM-in-LLM 크론 루프 해결 — 3개 잡 제거 → host systemd 타이머 이전
- [x] ML-012 · hermes-canary.timer (09:00), hermes-dspy-optimize.timer (12:00), hermes-dspy-remind.timer (18:00)
- [x] ML-013 · Hermes cron 잡 정체성 수정 — workdir=/opt/hermes/data 지정으로 SOUL.md 로드
- [x] ML-003 · scripts/discord-dm.py 작성 — Discord Bot API 직접 호출 (LLM 우회)
- [x] ML-003 · scripts/hermes-notify 작성 — Claude Code → 사용자 알림 전송
- [x] ML-003 · Hermes 자발적 Discord DM 확인 ✓ (Carnice-9b 정체성, 한국어, 네이티브 환경)
- [x] ML-003 · morning-curiosity 크론 잡 등록 (매일 09:00 KST, SOUL.md 로드됨)
- [x] ML-003 · AGENTS.md, SOUL.md, config.yaml 네이티브 환경 기준으로 업데이트

## Phase 10 — Hermes 행동 교정 + DSPy 완성 (2026-04-26)
- [x] ML-003 · AGENTS.md 행동 규칙 강화 — 3회 실패 중단, 파일 수정 7단계 절차, git 작성자 규칙
- [x] ML-003 · AGENTS.md 에이전트 설정 변경 후 검증 체크리스트 추가 (systemctl→journalctl→grep)
- [x] ML-014 · DSPy dataset.json 네이티브 환경 재작성 (37 케이스, must_not_contain 버그 수정)
- [x] ML-014 · evaluate.py: enable_thinking=False, max_tokens=4096, load_signature() 통합
- [x] ML-014 · optimize.py: Docker 시대 하드코딩 제거, load_signature() 사용
- [x] ML-014 · cron_optimize.py: 전면 재작성 — 네이티브 경로, Hermes git 작성자, config 단일 소스
- [x] ML-014 · DSPy BootstrapFewShot 최적화 실행 → 78.4% → 86.5%
- [x] ML-014 · Verified Examples 수동 보완 (회귀 복구 + 미커버 케이스) → **100% (37/37)**
- [x] PVE-003 · VM 102 Windows 테스트 VM Terraform 코드 작성 (UEFI, TPM, VirtIO)
- [x] PVE-003 · VM 102 terraform apply 완료 (수동 qm create 잔해 정리 후 재생성)
- [x] ML-015 · Hermes VM 생성 IaC 강제 교정 — qm create → terraform apply DSPy 검증 42케이스 100%

## Backlog
- [x] PVE-004 · Terraform으로 VM 100 코드화 (import → apply, lifecycle ignore_changes 적용)
- [x] ML-006 · Hermes 스킬 확장 — terminal 툴 확인, AGENTS.md 인프라 컨텍스트 주입
- [x] GITOPS-003 · KAI Scheduler 제거 — 단일 GPU 추론 클러스터에 불필요, 미사용 확인 후 삭제
- [ ] PVE-003 · VM 102 Windows 설치 완료 (ISO 다운로드 후 terraform apply + 수동 설치)
- [ ] K8S-003 · 워커 노드 추가 확장 (물리 머신 확보 시)
- [ ] ML-007 · 더 큰 모델 검토 (GPU 증설 시 — 현재 계획 없음)
