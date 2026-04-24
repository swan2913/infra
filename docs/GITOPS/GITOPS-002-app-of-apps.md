# GITOPS-002 · App-of-Apps 구조 및 앱 추가 방법

> 패턴: ArgoCD App-of-Apps  
> 완료일: 2026-04-25

## 구조

```
clusters/ubuntu-1/argocd-apps/
├── root.yaml            ← 이 디렉토리 전체를 관리하는 루트 앱
├── gpu-operator.yaml    ← NVIDIA GPU Operator (Helm, helm.ngc.nvidia.com)
├── kai-scheduler.yaml   ← KAI Scheduler (git 래퍼 → OCI ghcr.io)
└── vllm.yaml            ← vLLM 추론 서버 (git charts/vllm)
```

## 새 앱 추가하는 법

1. `clusters/ubuntu-1/argocd-apps/myapp.yaml` 생성

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: myapp
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: git@github.com:swan2913/infra.git
    targetRevision: main
    path: charts/myapp          # git 내 Helm 차트 경로
  destination:
    server: https://kubernetes.default.svc
    namespace: myapp
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

2. `git add -A && git commit -m "feat: add myapp" && git push`
3. ArgoCD root 앱이 자동 감지 → myapp Application 생성 → 배포

## OCI Helm 차트 처리 방법

ArgoCD가 OCI 레지스트리를 직접 참조하면 index.yaml 오류 발생.  
→ `charts/<name>/` 에 래퍼 Chart.yaml + Chart.lock 생성하는 방식 사용.

```bash
# 래퍼 차트 생성 예시 (kai-scheduler)
mkdir -p charts/myoci
cat > charts/myoci/Chart.yaml << 'EOF'
apiVersion: v2
name: myoci
version: 1.0.0
dependencies:
  - name: myapp
    version: v1.2.3
    repository: oci://ghcr.io/org/myapp
EOF

mkdir -p /tmp/myoci-tmp && cp charts/myoci/Chart.yaml /tmp/myoci-tmp/
cd /tmp/myoci-tmp && helm dependency update
cp Chart.lock ~/infra/charts/myoci/
```

## 앱별 Helm values 변경 방법

```bash
# 예: vLLM 모델 변경
vim charts/vllm/values.yaml
# model: "google/gemma-3-12b-it-qat"

git add -A && git commit -m "feat: upgrade vllm model to 12B" && git push
# → ArgoCD 자동 반영 (약 1분)
```

## 수동 강제 Sync

```bash
# 특정 앱만
kubectl patch app vllm -n argocd \
  --type merge \
  -p '{"operation":{"initiatedBy":{"username":"admin"},"sync":{"syncStrategy":{"apply":{}}}}}'

# 전체 앱 상태 확인
kubectl get app -n argocd -o wide
```
