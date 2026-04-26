# ML-003 · Hermes Agent 운영

> PVE 호스트 네이티브 설치, Discord 인터페이스  
> 최종 갱신: 2026-04-26 (Docker → 네이티브 전환 ML-011, cron workdir 규칙 ML-013)

## 구성 개요

```
Discord ──→ Hermes Gateway (PVE 호스트, ksh 계정)
                │
                ├──→ llama.cpp API (http://192.168.1.24:30800/v1)
                ├──→ ssh vm100 kubectl (k3s 클러스터)
                ├──→ ssh vm100 / ssh vm101
                ├──→ sudo qm (PVE VM 관리)
                └──→ sudo docker / sudo systemctl (호스트 서비스)
```

## 설치 경로

| 항목 | 경로 |
|------|------|
| 소스 | `/opt/hermes-agent/` |
| 실행 바이너리 | `/opt/hermes-agent/.venv/bin/hermes` |
| 데이터 디렉토리 | `/opt/hermes/data/` |
| 환경변수 파일 | `/opt/hermes/.env` |
| systemd 서비스 | `/etc/systemd/system/hermes.service` |
| 설정 git 정본 | `~/infra/hermes/` |

---

## 상태 확인

```bash
# 서비스 상태
sudo systemctl status hermes

# 실시간 로그
sudo journalctl -u hermes -f

# 최근 로그 50줄
sudo journalctl -u hermes -n 50 --no-pager

# Discord 연결 확인
sudo journalctl -u hermes -n 20 | grep -E "(Discord|Connected|ERROR)"

# 버전 확인
/opt/hermes-agent/.venv/bin/hermes --version
```

---

## 서비스 관리

```bash
# 재시작 (config 변경 후 항상 필요)
sudo systemctl restart hermes

# 중지 / 시작
sudo systemctl stop hermes
sudo systemctl start hermes

# 부팅 자동시작 활성화 확인
sudo systemctl is-enabled hermes
```

---

## 설정 변경 → 반영

```bash
# 1. git 정본 수정
vi ~/infra/hermes/config.yaml   # system prompt, Verified Examples
vi ~/infra/hermes/AGENTS.md     # 행동 규칙
vi ~/infra/hermes/SOUL.md       # 정체성

# 2. commit & push
cd ~/infra && git add hermes/ && git commit -m "hermes: ..." && git push

# 3. 재시작 (ExecStartPre가 infra/hermes/ → /opt/hermes/data/ 복사)
sudo systemctl restart hermes
```

> **주의**: `/opt/hermes/data/config.yaml` 직접 수정 금지 — 재시작 시 덮어씌워진다.

---

## Discord 알림 전송 (Claude Code → 사용자)

```bash
~/infra/scripts/hermes-notify "메시지 내용"
```

내부 동작: `scripts/discord-dm.py` → Discord Bot REST API 직접 호출 (LLM 우회).

---

## 자동화 타이머 (Host Systemd)

```bash
# 타이머 목록 및 다음 실행 시간
sudo systemctl list-timers hermes-* --no-pager

# 특정 타이머 수동 즉시 실행
sudo systemctl start hermes-canary.service
sudo systemctl start hermes-dspy-optimize.service
sudo systemctl start hermes-dspy-remind.service

# 타이머 로그
sudo journalctl -u hermes-canary.service -n 20
sudo journalctl -u hermes-dspy-optimize.service -n 20
```

| 타이머 | 시간 (KST) | 역할 |
|--------|-----------|------|
| `hermes-canary.timer` | 09:00 | 응답 품질 캐너리 검사 |
| `hermes-dspy-optimize.timer` | 12:00 | DSPy 자동 최적화 |
| `hermes-dspy-remind.timer` | 18:00 | 최적화 후 재시작 리마인더 |

LLM 우회 실행 — Hermes 내부 크론 사용 안 함 (LLM-in-LLM 루프 방지, ML-012 참조).

---

## Hermes 내장 크론 잡

### ⚠️ 필수: --workdir 반드시 지정

workdir 없이 생성된 잡은 SOUL.md·AGENTS.md를 로드하지 않아 기본 "Nous Research" 정체성을 사용한다.

```bash
# 잡 목록
HERMES_HOME=/opt/hermes/data /opt/hermes-agent/.venv/bin/hermes cron list

# 잡 생성 (--workdir 필수)
HERMES_HOME=/opt/hermes/data /opt/hermes-agent/.venv/bin/hermes cron create \
  --name "job-name" \
  --deliver "discord:1497321508379426897" \
  --workdir "/opt/hermes/data" \
  "0 9 * * *" \
  "프롬프트 내용"

# 잡 삭제
HERMES_HOME=/opt/hermes/data /opt/hermes-agent/.venv/bin/hermes cron delete <job_id>
```

### 현재 등록된 잡

| 이름 | 스케줄 | 역할 |
|------|--------|------|
| `morning-curiosity` | 매일 09:00 KST | 인프라 이상·패턴 관찰 보고 (없으면 [SILENT]) |

### Discord DM 채널 ID

| 채널 | ID |
|------|-----|
| goseunghwan_54963 DM | `1497321508379426897` |

---

## DSPy 수동 실행

```bash
# 평가만 (config 변경 없음)
cd ~/infra/dspy && .venv/bin/python3 evaluate.py

# 최적화 + config.yaml 갱신 + Discord 보고
~/infra/scripts/run-dspy-optimize.sh

# 캐너리 수동 실행
python3 ~/infra/scripts/hermes-canary.py
```

---

## 호스트 접근 명령어 (네이티브 설치 이후 가능)

```bash
# VM 목록 / 상태 / 재시작
sudo qm list
sudo qm status 100
sudo qm reboot 101

# k8s (kubectl은 vm100에 있음)
ssh vm100 kubectl get nodes
ssh vm100 kubectl get pods -A
ssh vm100 kubectl get app -n argocd

# 컨테이너 관리
sudo docker ps
sudo docker logs <container>

# 서비스 관리
sudo systemctl status <service>
sudo systemctl restart <service>
```

---

## hermes.service 변경 시

```bash
vi ~/infra/hermes/hermes.service

sudo cp ~/infra/hermes/hermes.service /etc/systemd/system/hermes.service
sudo systemctl daemon-reload
sudo systemctl restart hermes
```

---

## 업데이트 / 재설치

```bash
# hermes-agent 소스 갱신 (컨테이너에서 재추출)
sudo docker pull nousresearch/hermes-agent:latest
sudo docker create --name hermes-tmp nousresearch/hermes-agent:latest
sudo docker cp hermes-tmp:/opt/hermes/. /opt/hermes-agent/
sudo docker rm hermes-tmp
sudo rm -rf /opt/hermes-agent/.venv /opt/hermes-agent/data

# venv 재생성
sudo python3 -m venv /opt/hermes-agent/.venv
sudo /opt/hermes-agent/.venv/bin/pip install -e "/opt/hermes-agent[messaging,cron,pty]"

sudo systemctl restart hermes
```

---

## git 관리 제외 항목 (`/opt/hermes/` 전용)

| 파일/디렉토리 | 내용 |
|--------------|------|
| `.env` | Discord 토큰, API 키, GitHub 토큰 |
| `data/cron/jobs.json` | 런타임 크론 잡 상태 |
| `data/sessions/` | 대화 세션 기록 |
| `data/memories/` | 에이전트 메모리 |
| `data/logs/` | 런타임 로그 |
