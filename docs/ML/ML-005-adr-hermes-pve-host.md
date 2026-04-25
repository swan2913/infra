# ML-005 · ADR: Hermes Agent 실행 위치 — k8s → PVE 호스트 systemd

> 작성일: 2026-04-25  
> 상태: 채택

## 배경

Hermes는 자율 인프라 에이전트다. 목표는 Discord 명령 하나로 VM 생성, k8s 앱 배포, 모델 교체까지 전체 스택을 자동화하는 것이다.

초기 배포는 k8s Deployment(namespace: hermes)로 구성했으나, 운영 중 한계가 드러났다.

## 선택지

### A. k8s pod 유지 + Proxmox API 접근권 부여

Hermes pod에 Proxmox API 토큰을 Secret으로 주입하고 REST API(`https://192.168.1.94:8006`)로 PVE를 제어한다.

**장점**
- 현재 GitOps 패턴 유지
- 배포·재시작이 ArgoCD로 관리됨

**단점**
- Proxmox REST API만 사용 가능 — `pveum`, `qm`, `pct` 등 CLI 명령 불가
- Terraform, Ansible 바이너리가 컨테이너 안에 없음 → IaC 실행 불가
- SSH로 VM 내부 접근 시 키 관리 복잡도 증가
- **인프라 전자동화 목표를 달성할 수 없음**

### B. PVE 호스트에서 systemd 서비스로 실행 ✅ 채택

Hermes를 k8s에서 제거하고 PVE 호스트(`192.168.1.94`)에 systemd 서비스로 설치한다.

**장점**
- `terraform`, `ansible`, `pveum`, `qm`, `kubectl` 전부 직접 실행 가능
- SSH로 VM 100·101 자유롭게 접근 가능
- 인프라 전체 스택(PVE → VM → k8s → 앱)을 단일 에이전트가 제어
- PVE 재부팅 후 자동 시작(systemd)

**단점**
- ArgoCD GitOps 관리 범위에서 벗어남
- 로그·재시작은 `journalctl`/`systemctl`로 관리
- 컨테이너 격리 없음 → 에이전트 오동작 시 호스트 영향 가능

### C. 별도 "인프라 러너" 서비스 구성

PVE 호스트에 Terraform/Ansible을 실행하는 API 서버를 두고 Hermes가 HTTP로 호출하는 구조.

**단점**
- 구현 복잡도 과도함
- Hermes 툴 시스템이 있는데 중간 레이어 불필요

## 결정

**B 채택.** 인프라 전자동화가 핵심 목표이므로 실행 환경의 권한 범위가 가장 중요하다. GitOps 원칙은 앱 레이어(k8s)에 유지하고, 에이전트 자체는 하이퍼바이저 레벨에서 실행한다.

## 영향

- `clusters/ubuntu-1/argocd-apps/hermes.yaml` 삭제 (ArgoCD 앱 제거)
- `charts/hermes/` 유지 (기록 보존, 향후 재검토 가능)
- PVE 호스트에 `/etc/systemd/system/hermes.service` 추가
- Hermes 설정·데이터는 `/opt/hermes/` 에 보관
- Discord 봇 토큰, GitHub PAT 등 민감 정보는 `/opt/hermes/.env` (root 소유, 600)
