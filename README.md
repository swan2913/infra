# infra

Proxmox VE + k3s + GPU 패스스루 + GitOps 기반 AI 추론 서버 홈랩.  
GitHub가 단일 원천 — ArgoCD가 자동으로 클러스터에 반영.

---

## 아키텍처

```
[Proxmox VE 9.1.1 | 192.168.1.94]
  Ryzen 5 5600X / 62GB RAM / RTX 3080 10GB

  ├─ VM 100: ubuntu-1 (192.168.1.234)
  │    k3s Control Plane / 4코어 / 4GB
  │
  └─ VM 101: worker-gpu (192.168.1.24)
       k3s Worker / 8코어 / 16GB / RTX 3080 PCIe Passthrough
       llama.cpp + Carnice-9b-Q6_K 추론 서버
```

**GitOps 흐름**
```
git push → GitHub (swan2913/infra)
               ↓ ArgoCD 자동 동기화 (1분)
           k3s 클러스터
               ├─ gpu-operator    Synced ✓
               ├─ kai-scheduler   Synced ✓
               └─ vllm            Synced ✓ (llama.cpp, Carnice-9b-Q6_K)
```

---

## 접속 정보

| 시스템 | 주소 |
|--------|------|
| PVE 웹 UI | https://192.168.1.94:8006 |
| VM SSH | `ssh vm100` |
| ArgoCD UI | https://192.168.1.234:30443 |
| llama.cpp API | http://192.168.1.24:30800 |

---

## 디렉토리 구조

```
infra/
├── CLAUDE.md                        # 전역 에이전트 규칙
├── clusters/ubuntu-1/argocd-apps/   # ArgoCD App 정의 (App-of-Apps)
├── charts/                          # Helm 차트 (vllm, kai-scheduler 래퍼)
├── terraform/proxmox/               # Proxmox VM 프로비저닝
├── ansible/                         # VM 내부 설정 자동화
└── docs/                            # 도메인별 문서
    ├── CHECKLIST.md                 # 작업 체크리스트
    ├── PVE/                         # Proxmox 설정
    ├── GPU/                         # GPU 드라이버
    ├── K8S/                         # k3s 클러스터
    ├── GITOPS/                      # ArgoCD
    ├── IaC/                         # Terraform, Ansible
    └── ML/                          # vLLM, 모델
```

---

## 현재 상태

| 항목 | 버전 | 상태 |
|------|------|------|
| Proxmox VE | 9.1.1 | 운영 중 |
| k3s | v1.34.6+k3s1 | Ready |
| NVIDIA Driver | 580.126.09 | VM 100 |
| GPU Operator | v26.3.1 | Synced |
| KAI Scheduler | v0.5.4 | Synced |
| llama.cpp + Carnice-9b-Q6_K | v0.3.5 | Running (http://192.168.1.24:30800) |

→ 체크리스트: [docs/CHECKLIST.md](docs/CHECKLIST.md)
