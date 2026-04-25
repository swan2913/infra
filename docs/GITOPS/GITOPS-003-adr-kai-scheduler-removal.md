# GITOPS-003 · ADR: KAI Scheduler 제거

> 작성일: 2026-04-25  
> 상태: 채택

## 배경

초기 구성 시 GPU 워크로드 스케줄링을 위해 KAI Scheduler(v0.5.4)를 설치했다. 클러스터가 추론 서버 전용으로 확정된 시점에 필요성을 재검토했다.

## 조사 결과

```bash
kubectl get pods -A -o jsonpath=... | grep -v default-scheduler
# 출력 없음 — 모든 파드가 default-scheduler 사용
```

- KAI Scheduler 파드(binder, podgrouper, scheduler) 3개 실행 중
- 실제로 KAI scheduler를 사용하는 워크로드: **0개**
- llama.cpp: 단일 파드, 단일 GPU — gang scheduling 대상 아님

## KAI Scheduler가 필요한 경우

- 다수의 GPU를 동시에 점유해야 하는 분산 학습 잡 (tensor parallel across nodes)
- 여러 파드가 묶음으로 스케줄돼야 하는 batch 워크로드 (PodGroup)
- 공유 GPU, 시분할(time-slicing) 고급 정책

## 현재 클러스터와의 불일치

| 항목 | KAI 필요 조건 | 현재 클러스터 |
|------|-------------|-------------|
| GPU 수 | 다수 | 1개 (RTX 3080) |
| 워크로드 유형 | 분산 학습/배치 | 단일 추론 서버 |
| 노드 수 | 다수 워커 | 워커 1개 |
| PodGroup 사용 | 필수 | 없음 |

## 결정

**KAI Scheduler 제거.** 리소스(CPU/메모리) 절약, 클러스터 단순화.  
향후 멀티 GPU 분산 학습이 필요해지면 재설치한다.

## 영향

- `clusters/ubuntu-1/argocd-apps/kai-scheduler.yaml` 삭제
- `charts/kai-scheduler/` 유지 (기록 보존)
- ArgoCD prune으로 kai-scheduler 네임스페이스 자동 삭제
