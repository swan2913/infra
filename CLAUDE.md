# 전역 에이전트 규칙 (CLAUDE.md)

## 프로젝트 개요
Proxmox VE 위에 k3s + GPU 패스스루 + GitOps로 llama.cpp 추론 서버와 Hermes 자율 인프라 에이전트를 구축하는 홈랩 인프라.

## 핵심 원칙

### GitOps 단일 원천
- **모든 변경은 git push → ArgoCD 자동 반영** 이 원칙.
- `kubectl apply` 직접 실행은 테스트/긴급 목적에만 허용. 반드시 이후 git에 반영.
- 인프라 변경은 Terraform, VM 내 설정은 Ansible, 앱 배포는 Helm(ArgoCD) 순서로.

### 문서화
- 새 작업 완료 시 해당 도메인 폴더에 `도메인코드-번호-제목.md` 추가.
- `docs/CHECKLIST.md` 를 항상 최신 상태로 갱신.
- 명령어는 도메인별 문서에, README는 개요/구조/접속정보만.

### 보안
- 비밀번호, API 토큰, SSH 키는 절대 git commit 하지 않음.
- 민감 정보는 `*.tfvars`, k8s Secret, `.env` 로 관리 (모두 .gitignore).
- HuggingFace 토큰 등은 k8s Secret으로 주입.

## 환경 정보

| 항목 | 값 |
|------|-----|
| PVE 호스트 | 192.168.1.94 (ksh@pve) |
| VM 100 (CP) | 192.168.1.234 (ubuntu@ubuntu-1) |
| VM 101 (Worker) | 192.168.1.24 (ubuntu@worker-gpu) |
| SSH VM 접속 | `ssh vm100` 또는 `ssh vm101` (PVE 호스트에서) |
| kubectl | `ssh vm100 kubectl ...` 또는 VM 직접 접속 |
| ArgoCD UI | https://192.168.1.234:30443 |
| infra 리포 | ~/infra (git@github.com:swan2913/infra.git) |
| LLM 엔드포인트 (외부) | http://192.168.1.24:30800 |
| LLM 엔드포인트 (클러스터 내) | http://vllm.vllm.svc.cluster.local:8000/v1 |
| LLM 모델 | Carnice-9b-Q6_K.gguf (llama.cpp, 128K ctx) |
| Hermes Agent | namespace: hermes, Discord 봇 인터페이스 |

## 도메인 코드 체계

| 코드 | 도메인 | 담당 범위 |
|------|--------|-----------|
| PVE | Proxmox VE | 호스트 설정, VM 생성/관리, 네트워크 |
| GPU | GPU | 패스스루, 드라이버, Container Toolkit |
| K8S | Kubernetes | k3s, 노드, 네임스페이스, 리소스 |
| GITOPS | GitOps | ArgoCD, App-of-Apps, 배포 흐름 |
| IaC | Infra as Code | Terraform (Proxmox), Ansible (VM 내부) |
| ML | Machine Learning | llama.cpp, 모델, 추론 API, Hermes Agent |

## 작업 전 체크

```bash
# 클러스터 상태
ssh vm100 kubectl get nodes
ssh vm100 kubectl get app -n argocd -o wide

# llama.cpp / Hermes 상태
ssh vm100 kubectl get pods -n vllm
ssh vm100 kubectl get pods -n hermes

# 변경 전 git 상태
cd ~/infra && git status && git log --oneline -5
```

## 파일 구조 규칙
- Helm values 변경 → `charts/<name>/values.yaml`
- 새 앱 추가 → `clusters/ubuntu-1/argocd-apps/<name>.yaml`
- VM 리소스 변경 → `terraform/proxmox/main.tf`
- VM 내 설정 변경 → `ansible/playbooks/<action>.yml`
- 문서 추가 → `docs/<DOMAIN>/<DOMAIN>-<NNN>-<slug>.md`
