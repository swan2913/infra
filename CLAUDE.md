# 전역 에이전트 규칙 (CLAUDE.md)

## 프로젝트 개요
Proxmox VE 위에 k3s + GPU 패스스루 + GitOps로 llama.cpp 추론 서버와 Hermes 자율 인프라 에이전트를 구축하는 홈랩 인프라.

## 핵심 원칙

### 아키텍처 원칙
- **책임 경계**: 각 노드는 단일 역할. 편의를 위한 통합은 하지 않는다.
- **장애 내성**: control plane과 워크로드는 반드시 분리. GPU 장애가 클러스터 전체 장애가 되어선 안 된다.
- **IaC 우선**: 노드 추가/제거는 Terraform으로. 수동 변경 후 코드 역반영은 금지.

### GitOps 단일 원천
- **모든 변경은 git push → ArgoCD 자동 반영** 이 원칙.
- `kubectl apply` 직접 실행은 테스트/긴급 목적에만 허용. 반드시 이후 git에 반영.
- 인프라 변경은 Terraform, VM 내 설정은 Ansible, 앱 배포는 Helm(ArgoCD) 순서로.

### 문서화
- 새 작업 완료 시 해당 도메인 폴더에 `도메인코드-번호-제목.md` 추가.
- `docs/CHECKLIST.md` 를 항상 최신 상태로 갱신.
- 명령어는 도메인별 문서에, README는 개요/구조/접속정보만.
- **아키텍처 의사결정은 반드시 문서화**: 선택지(A/B/C), 선택 이유, 포기한 대안과 그 이유를 `docs/<DOMAIN>/<DOMAIN>-NNN-adr-제목.md`에 기록. 나중에 "왜 이렇게 했지?"라는 질문에 git log만으로 답할 수 없을 때를 위해.

### 보안
- 비밀번호, API 토큰, SSH 키는 절대 git commit 하지 않음.
- 민감 정보는 `*.tfvars`, k8s Secret, `.env` 로 관리 (모두 .gitignore).
- HuggingFace 토큰 등은 k8s Secret으로 주입.
- `.example` 파일에도 실제 값 사용 금지 — 반드시 `<YOUR-TOKEN-UUID>` 형식 플레이스홀더 사용.
- 문서/주석의 명령어 예시에도 실제 토큰/패스워드 기재 금지.
- 토큰이 노출된 경우: 히스토리 정리보다 **즉시 폐기·재발급이 먼저** (참고: IaC-003).
- commit 전 확인: `git diff --cached | grep -E "(password|token|secret)\s*=\s*\"[^<]"`

## 환경 정보

| 항목 | 값 |
|------|-----|
| PVE 호스트 | 192.168.1.94 (ksh@pve) — 하이퍼바이저, Hermes Agent, Terraform/Ansible |
| VM 100 (CP) | 192.168.1.234 (ubuntu@ubuntu-1) — k3s control plane, ArgoCD |
| VM 101 (Worker) | 192.168.1.24 (ubuntu@worker-gpu) — k3s worker, GPU 워크로드, llama.cpp |
| SSH VM 접속 | `ssh vm100` 또는 `ssh vm101` (PVE 호스트에서) |
| kubectl | `ssh vm100 kubectl ...` 또는 VM 직접 접속 |
| ArgoCD UI | https://192.168.1.234:30443 |
| infra 리포 | ~/infra (git@github.com:swan2913/infra.git) |
| LLM 엔드포인트 (외부) | http://192.168.1.24:30800 |
| LLM 엔드포인트 (클러스터 내) | http://vllm.vllm.svc.cluster.local:8000/v1 |
| LLM 모델 | Carnice-9b-Q6_K.gguf (llama.cpp, 128K ctx) |
| Hermes Agent | PVE 호스트 systemd 서비스, Discord 봇 인터페이스 |

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

# llama.cpp 상태
ssh vm100 kubectl get pods -n vllm

# Hermes Agent 상태 (PVE 호스트 systemd)
sudo systemctl status hermes
sudo journalctl -u hermes -n 20

# 변경 전 git 상태
cd ~/infra && git status && git log --oneline -5
```

## 파일 구조 규칙
- Helm values 변경 → `charts/<name>/values.yaml`
- 새 앱 추가 → `clusters/ubuntu-1/argocd-apps/<name>.yaml`
- VM 리소스 변경 → `terraform/proxmox/main.tf`
- VM 내 설정 변경 → `ansible/playbooks/<action>.yml`
- 문서 추가 → `docs/<DOMAIN>/<DOMAIN>-<NNN>-<slug>.md`

## Hermes Agent 관리 규칙

### 실행 환경
- **네이티브 설치** — Docker 없이 PVE 호스트에 직접 설치
- 소스: `/opt/hermes-agent/` (hermes-agent v0.11.0 editable install)
- venv: `/opt/hermes-agent/.venv/bin/hermes`
- 실행 계정: `ksh` (sudo NOPASSWD:ALL → qm/systemctl/docker 등 전체 접근 가능)
- 데이터: `/opt/hermes/data/`
- 환경변수: `/opt/hermes/.env`

### 설정 파일 위치 (git 정본)
| 파일 | 경로 | 역할 |
|------|------|------|
| `config.yaml` | `hermes/config.yaml` | 모델 설정, system prompt, Verified Examples |
| `AGENTS.md` | `hermes/AGENTS.md` | 에이전트 행동 규칙, 서비스 위치 참조 |
| `SOUL.md` | `hermes/SOUL.md` | 에이전트 정체성, 소통 방식 |
| `hermes.service` | `hermes/hermes.service` | systemd 서비스 정의 |

### 수정 → 반영 절차
```bash
# 1. infra 레포에서 파일 수정
vi ~/infra/hermes/config.yaml   # 또는 AGENTS.md, SOUL.md

# 2. git commit
cd ~/infra && git add hermes/ && git commit -m "hermes: ..." && git push origin main

# 3. 서비스 재시작 (ExecStartPre가 infra/hermes/ → /opt/hermes/data/ 복사)
sudo systemctl restart hermes
```

### hermes.service 변경 시
```bash
sudo cp ~/infra/hermes/hermes.service /etc/systemd/system/hermes.service
sudo systemctl daemon-reload && sudo systemctl restart hermes
```

### git 관리 제외 항목 (`/opt/hermes/data/` 전용)
- `.env` — Discord 토큰, API 키
- `vm_key` — SSH 개인키
- `state.db` — 런타임 상태
- `sessions/`, `memories/`, `logs/` — 런타임 데이터

### 주의
- `/opt/hermes/data/config.yaml`을 직접 수정하지 않는다 — 재시작 시 덮어씌워진다.
- hermes-agent 업데이트: `sudo /opt/hermes-agent/.venv/bin/pip install -e /opt/hermes-agent`

### Discord 알림 (Claude Code → 사용자)
```bash
~/infra/scripts/hermes-notify "메시지"
```
내부적으로 `scripts/discord-dm.py` → Discord Bot API 직접 호출 (LLM 우회).

### 자동화 스케줄 (systemd 타이머)
| 타이머 | 시간 (KST) | 역할 |
|--------|-----------|------|
| `hermes-canary.timer` | 09:00 | Hermes 응답 품질 캐너리 검사 |
| `hermes-dspy-optimize.timer` | 12:00 | DSPy BootstrapFewShot 자동 최적화 |
| `hermes-dspy-remind.timer` | 18:00 | 최적화 후 재시작 리마인더 |

모두 host systemd 타이머로 실행 — Hermes LLM 경유 없음 (LLM-in-LLM 루프 방지).
