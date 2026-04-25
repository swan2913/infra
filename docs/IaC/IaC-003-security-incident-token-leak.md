# IaC-003 · 보안 인시던트: Proxmox API 토큰 Git 노출 및 대응

> 작성일: 2026-04-25

## 무엇이 잘못됐나

`terraform/proxmox/terraform.tfvars.example` 파일에 실제 Proxmox API 토큰이 하드코딩된 채 commit되었다.

```
# commit f3d616f — feat: add worker GPU node IaC and vLLM inference setup
proxmox_api_token = "terraform@pve!terraform=4d3a9435-947c-47d0-a0c9-56ff3d968814"
```

추가로 `docs/IaC/IaC-001-terraform-proxmox.md` 문서에도 토큰 앞부분이 예시 코드에 포함되었다.

```
# proxmox_api_token = "terraform@pve!terraform=4d3a9435-..."
```

두 파일 모두 GitHub 공개 히스토리에 노출되었다.

## 왜 올라갔나

`terraform.tfvars`는 `.gitignore`로 제외되어 있었으나, **`.example` 파일은 제외 대상이 아니었다**.  
예시 파일을 만들 때 실제 값을 그대로 복사해 넣고 플레이스홀더로 교체하지 않은 채 commit했다.

문서 파일은 작성 중 명령어 예시를 실제 토큰으로 적어둔 것이 그대로 commit되었다.

## 어떻게 고쳤나

1. 토큰 플레이스홀더 교체
   - `terraform.tfvars.example`: `4d3a9435-...` → `<YOUR-TOKEN-UUID>`
   - `IaC-001-terraform-proxmox.md`: 동일 교체

2. `git filter-branch`로 전체 히스토리(32 커밋) 재작성
   ```bash
   git filter-branch --force --tree-filter '
     sed -i "s/4d3a9435-947c-47d0-a0c9-56ff3d968814/<YOUR-TOKEN-UUID>/g" \
       terraform/proxmox/terraform.tfvars.example
   ' -- --all
   ```

3. GitHub에 force push
   ```bash
   git push --force origin main
   ```

4. 로컬 정리
   ```bash
   git for-each-ref --format='%(refname)' refs/original/ | xargs -I{} git update-ref -d {}
   git reflog expire --expire=now --all
   git gc --prune=now
   ```

5. **기존 토큰 폐기 후 재발급** (가장 중요)
   ```bash
   pveum user token remove terraform@pve terraform
   pveum user token add terraform@pve terraform --privsep=0
   ```
   `terraform/proxmox/terraform.tfvars`에 새 토큰 반영 완료.

## 앞으로 어떻게 해야 하나

### 규칙 1 — `.example` 파일에는 절대 실제 값 사용 금지

```
# 올바른 예시 파일 작성법
proxmox_api_token = "terraform@pve!terraform=<YOUR-TOKEN-UUID>"
proxmox_ssh_password = "<YOUR-ROOT-PASSWORD>"
vm_ssh_public_key = "ssh-ed25519 AAAA... user@host"
```

플레이스홀더 형식: `<대문자_설명>`

### 규칙 2 — 민감 정보 파일 `.gitignore` 규칙

```gitignore
# 실제 값이 담긴 파일 — 절대 commit 금지
*.tfvars
!*.tfvars.example   # example은 허용하되 실제 값 없어야 함
.env
*.env.local
k8s/*-secret.yaml
```

### 규칙 3 — commit 전 체크리스트

```bash
# commit 전 민감 정보 스캔
git diff --cached | grep -E "(password|token|secret|key)\s*=\s*\"[^<]" && echo "⚠️ 민감 정보 의심"
```

### 규칙 4 — 문서에 실제 값 절대 기재 금지

명령어 예시에는 항상 플레이스홀더 사용:
```bash
# 잘못된 예
proxmox_api_token = "terraform@pve!terraform=4d3a9435-947c-47d0-a0c9-56ff3d968814"

# 올바른 예
proxmox_api_token = "terraform@pve!terraform=<YOUR-TOKEN-UUID>"
```

### 규칙 5 — 토큰이 노출됐다면 즉시 폐기

노출된 토큰은 히스토리를 지워도 이미 캐시되었을 수 있다. **히스토리 정리보다 토큰 폐기가 먼저다.**

```bash
# Proxmox 토큰 즉시 폐기
sudo pveum user token remove <user>@pve <tokenid>
sudo pveum user token add <user>@pve <tokenid> --privsep=0
```

## 타임라인

| 시각 | 이벤트 |
|------|--------|
| 2026-04-25 03:xx | commit f3d616f — 토큰 포함 채 GitHub push |
| 2026-04-25 (당일) | 보안 스캔 중 발견 |
| 2026-04-25 (당일) | filter-branch 히스토리 재작성 + force push |
| 2026-04-25 (당일) | 구 토큰 폐기, 새 토큰 `166a9140-...` 발급 |
| 2026-04-25 (당일) | terraform.tfvars 새 토큰으로 교체 완료 |
