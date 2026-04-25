# K8S-001 · ADR: Control Plane 분리 유지 (VM 100 전용)

> 작성일: 2026-04-25  
> 상태: 채택

## 배경

Hermes Agent가 PVE 호스트로 이전된 후, VM 100(control plane)에 GPU도 없고 앱 워크로드도 없는 상태가 되었다. VM 101(worker-gpu)에 k3s를 단일 노드로 통합하고 VM 100을 제거하는 방안이 검토되었다.

## 결정

**VM 100 유지 — control plane 전용으로 역할 고정.**

## 이유

### 1. 책임 경계
- VM 100: 클러스터 제어 (API server, etcd, scheduler, ArgoCD)
- VM 101: 워크로드 실행 (GPU 추론, 앱 파드)
- 두 역할이 같은 노드에 있으면 경계가 흐려지고 운영 판단이 어려워진다

### 2. 장애 내성
- VM 101(GPU 워크로드)에 장애가 나도 control plane은 살아있다
- ArgoCD, kubectl 접근, 클러스터 상태 확인이 계속 가능
- 단일 노드라면 GPU 드라이버 크래시 = 클러스터 전체 다운

### 3. IaC 관리 원칙
- VM은 Terraform으로 코드화된 자원이다
- "리소스 낭비"를 이유로 수동으로 통합하면 Terraform state와 실제가 달라진다
- VM 추가/제거는 `main.tf` 변경 → `terraform apply` 순서를 지켜야 한다

## 포기한 대안

### VM 101 단일 노드 통합
- 장점: RAM/CPU 절약, 관리 대상 감소
- 단점: 책임 경계 소멸, GPU 장애 = 클러스터 전체 장애, Terraform state 불일치
- **채택하지 않음**

## VM 역할 정의 (확정)

| VM | IP | 역할 |
|----|-----|------|
| VM 100 (ubuntu-1) | 192.168.1.234 | k3s control plane, ArgoCD, kubectl 진입점 |
| VM 101 (worker-gpu) | 192.168.1.24 | k3s worker, GPU 워크로드, llama.cpp |
| PVE 호스트 | 192.168.1.94 | 하이퍼바이저, Hermes Agent, Terraform/Ansible 실행 |
