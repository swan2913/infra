# K8S 도메인 에이전트 규칙

## 담당 범위
k3s 클러스터, 노드 관리, 네임스페이스, 리소스 모니터링.

## 작업 원칙

- 네임스페이스/리소스 직접 생성은 ArgoCD App으로 관리 (수동 apply 지양)
- `kubectl delete` 는 ArgoCD prune 으로 대체 가능 — 직접 삭제 전 확인
- 워커 노드 추가 시 Ansible `setup-k3s-agent.yml` 사용
- k3s token은 민감 정보 — git에 올리지 않음

## 주요 명령어

```bash
# PVE 호스트에서 VM으로 kubectl 실행
ssh vm100 kubectl get nodes -o wide
ssh vm100 kubectl get pods -A
ssh vm100 kubectl top nodes

# GPU 리소스 확인
ssh vm100 kubectl describe node | grep -A5 "nvidia.com"

# k3s 서비스
ssh vm100 sudo systemctl status k3s
ssh vm100 sudo journalctl -u k3s -f
```

## 파일 위치
- k3s 설치 문서: `docs/K8S/K8S-001-k3s-install.md`
- Ansible agent 설치: `ansible/playbooks/setup-k3s-agent.yml`
