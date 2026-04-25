# ML-003 · Hermes Agent 배포

> vLLM(llama.cpp) 백엔드 기반 자율 인프라 에이전트, Discord 인터페이스  
> 상태: 완료 — 1/1 Running, Discord 연결 정상

## 개요

Hermes Agent는 Discord 봇 인터페이스로 자연어 명령을 받아 인프라 작업을 수행하는
자율 에이전트다. LLM 백엔드는 클러스터 내부의 llama.cpp 서버(ML-002)를 사용한다.

```
Discord ─→ Hermes Agent (k8s) ─→ llama.cpp 서버 (vllm namespace)
                │
                ├─→ kubectl (k8s 작업)
                └─→ GitHub API (코드/이슈 관리)
```

## 배포 구성

### 네임스페이스 및 이미지

| 항목 | 값 |
|------|-----|
| Namespace | `hermes` |
| 이미지 | `nousresearch/hermes-agent:latest` |
| Pull Policy | Always |
| 노드 | worker-gpu (GPU 노드, llama.cpp와 동일 머신) |

### config.yaml (ConfigMap)

```yaml
model: Carnice-9b-Q4_K_M.gguf
provider: custom
base_url: http://vllm.vllm.svc.cluster.local:8000/v1
context_length: 131072
```

`context_length: 131072` 지정 이유: Hermes는 최소 64K 컨텍스트를 요구하며,
llama.cpp 서버가 128K로 기동되어 있으므로 일치시켰다.

### PVC (영속 볼륨)

```yaml
size: 10Gi
storageClass: local-path
mountPath: /opt/data
```

세션 기록, 에이전트 메모리, 스킬 데이터가 `/opt/data` 아래에 저장된다.

### initContainer: config 복사 + 권한 설정

ConfigMap을 직접 마운트하면 read-only라 Hermes가 수정할 수 없다.
initContainer가 ConfigMap을 PVC로 복사하고 UID 10000으로 chown한다.

```yaml
initContainers:
  - name: init-config
    image: busybox
    command:
      - sh
      - -c
      - >
        cp /etc/hermes-config/config.yaml /opt/data/config.yaml &&
        chown 10000:10000 /opt/data/config.yaml &&
        echo "Config ready."
    volumeMounts:
      - name: config-template
        mountPath: /etc/hermes-config
      - name: data
        mountPath: /opt/data
```

## Secrets

### hermes-discord

```bash
kubectl create secret generic hermes-discord \
  --namespace hermes \
  --from-literal=bot-token="<DISCORD_BOT_TOKEN>" \
  --from-literal=allowed-users="<DISCORD_USER_ID_1,ID_2>"
```

| 키 | 설명 |
|------|-----|
| `bot-token` | Discord 봇 토큰 |
| `allowed-users` | 봇 사용 허용 Discord 사용자 ID (쉼표 구분) |

### hermes-github

```bash
kubectl create secret generic hermes-github \
  --namespace hermes \
  --from-literal=token="<GITHUB_TOKEN>"
```

## Discord 봇 설정

Discord Developer Portal에서 다음 설정이 필요하다.

1. **Privileged Gateway Intents** 활성화 (필수):
   - Message Content Intent
   - Server Members Intent
   - Presence Intent

   이를 활성화하지 않으면 봇이 메시지 내용을 수신하지 못해 무응답 상태가 된다.

2. 봇 권한: `Send Messages`, `Read Message History`, `Add Reactions`

## 환경변수 주입

| 환경변수 | 출처 |
|----------|------|
| `HERMES_HOME` | `/opt/data` (하드코딩) |
| `DISCORD_BOT_TOKEN` | Secret `hermes-discord/bot-token` |
| `DISCORD_ALLOWED_USERS` | Secret `hermes-discord/allowed-users` (optional) |
| `DISCORD_IGNORE_NO_MENTION` | values.yaml `discord.ignoreMention` |
| `GITHUB_TOKEN` | Secret `hermes-github/token` |

## 해결된 이슈

### VLLM_PORT 환경변수 충돌

k8s가 자동으로 주입하는 `VLLM_PORT` 서비스 디스커버리 변수가 Hermes 내부 변수와
충돌했다. vllm namespace의 서비스가 존재하면 `VLLM_PORT=tcp://...` 형태로 주입된다.

**해결:** `enableServiceLinks: false` — Deployment 수준에서 자동 env 주입 비활성화.

### config.yaml read-only 문제

ConfigMap을 직접 볼륨으로 마운트하면 read-only 파일시스템이 된다. Hermes가
config 파일을 수정하려 해서 Permission Denied 에러가 발생했다.

**해결:** initContainer가 ConfigMap을 PVC로 복사한 뒤 chown 10000:10000 적용.

### Hermes 64K 컨텍스트 요구

Hermes Agent는 시작 시 모델의 context_length를 확인하고 64K 미만이면 거부한다.

**해결:** `config.yaml`에 `context_length: 131072` 명시.

## 파일 위치

| 파일 | 경로 |
|------|------|
| Helm Chart | `charts/hermes/` |
| values.yaml | `charts/hermes/values.yaml` |
| Deployment | `charts/hermes/templates/deployment.yaml` |
| PVC | `charts/hermes/templates/pvc.yaml` |
| ConfigMap | `charts/hermes/templates/configmap.yaml` |
| ArgoCD App | `clusters/ubuntu-1/argocd-apps/hermes.yaml` |

## 접속 및 상태 확인

```bash
# Pod 상태
ssh vm100 kubectl get pods -n hermes

# 로그 확인 (Discord 연결 메시지 확인)
ssh vm100 kubectl logs -n hermes deploy/hermes -f

# config 확인
ssh vm100 kubectl exec -n hermes deploy/hermes -- cat /opt/data/config.yaml
```

## 현재 상태

| 항목 | 상태 |
|------|------|
| Hermes Pod | 1/1 Running |
| Discord 연결 | 정상 |
| llama.cpp 연결 | http://vllm.vllm.svc.cluster.local:8000/v1 |
| 컨텍스트 | 128K |
