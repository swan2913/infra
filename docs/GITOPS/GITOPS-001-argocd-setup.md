# GITOPS-001 · ArgoCD 설치 및 GitHub 연동

> 환경: k3s v1.34.6 / ArgoCD stable  
> 완료일: 2026-04-25

## 설계 원칙
- GitHub `swan2913/infra` 리포가 **단일 원천(Single Source of Truth)**
- ArgoCD가 1분 주기로 폴링하여 클러스터에 자동 반영
- 수동 kubectl apply 금지 → 모든 변경은 git push로

## Step 1 · ArgoCD 설치

```bash
kubectl create namespace argocd

kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml \
  --server-side --force-conflicts

# 배포 완료 대기
kubectl rollout status deployment/argocd-server -n argocd --timeout=120s
```

## Step 2 · UI NodePort 노출

```bash
kubectl patch svc argocd-server -n argocd \
  --type merge \
  -p '{"spec":{"type":"NodePort","ports":[{"name":"https","port":443,"targetPort":8080,"nodePort":30443}]}}'

# 초기 admin 비밀번호
kubectl get secret argocd-initial-admin-secret \
  -n argocd -o jsonpath='{.data.password}' | base64 -d && echo
```

| URL | https://192.168.1.234:30443 |
|-----|-----|
| ID | admin |
| PW | `위 명령어로 확인` |

## Step 3 · GitHub Deploy Key 생성

```bash
# VM에서 생성
ssh-keygen -t ed25519 -f ~/.ssh/argocd_deploy_key -N "" -C "argocd@ubuntu-1"
cat ~/.ssh/argocd_deploy_key.pub
# → GitHub → infra repo → Settings → Deploy keys → Add (읽기 전용)
```

## Step 4 · ArgoCD에 GitHub 인증 Secret 등록

```bash
kubectl create secret generic argocd-repo-github \
  --namespace argocd \
  --from-literal=type=git \
  --from-literal=url=git@github.com:swan2913/infra.git \
  --from-file=sshPrivateKey=$HOME/.ssh/argocd_deploy_key

kubectl label secret argocd-repo-github -n argocd \
  argocd.argoproj.io/secret-type=repository
```

## Step 5 · Root App 적용 (App-of-Apps)

```bash
kubectl apply -f - << 'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: git@github.com:swan2913/infra.git
    targetRevision: main
    path: clusters/ubuntu-1/argocd-apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF
```

## 앱 배포 워크플로우

```bash
# PVE 호스트에서
cd ~/infra
# 파일 수정 후
git add -A && git commit -m "feat: ..." && git push
# → ArgoCD가 1분 내 자동 감지 및 반영
```

## 상태 확인

```bash
kubectl get app -n argocd -o wide
# NAME            SYNC STATUS   HEALTH STATUS   REVISION
# root            Synced        Healthy         main
# gpu-operator    Synced        Healthy         v26.3.1
# kai-scheduler   Synced        Healthy         v0.5.4
# vllm            OutOfSync     Missing         main      ← 워커 노드 추가 후 Sync
```
