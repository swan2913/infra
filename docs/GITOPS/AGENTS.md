# GITOPS 도메인 에이전트 규칙

## 담당 범위
ArgoCD 관리, App-of-Apps 구조, 배포 흐름.

## 작업 원칙

- **모든 배포는 git push → ArgoCD 자동 동기화** 로만 수행
- `kubectl apply` 직접 사용은 ArgoCD에서 곧 덮어씌워짐 (selfHeal: true)
- ArgoCD UI에서 수동 sync는 허용하지만 근본 원인은 git에 반영
- Deploy Key는 읽기 전용으로 유지

## App 추가 절차

1. `clusters/ubuntu-1/argocd-apps/<name>.yaml` 작성
2. `git add -A && git commit -m "feat: add <name> app" && git push`
3. root 앱이 자동 감지 → 신규 Application 생성 → 배포

## 상태 확인

```bash
ssh vm100 kubectl get app -n argocd -o wide
ssh vm100 kubectl describe app <name> -n argocd | grep -A5 Conditions
```

## 파일 위치
- ArgoCD 설치 문서: `docs/GITOPS/GITOPS-001-argocd-setup.md`
- App-of-Apps 구조: `docs/GITOPS/GITOPS-002-app-of-apps.md`
- App 정의: `clusters/ubuntu-1/argocd-apps/`
