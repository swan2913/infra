# ML-011 ADR: Hermes Agent Docker → 네이티브 설치 전환

**날짜**: 2026-04-26  
**상태**: 적용됨

---

## 문제

Hermes Agent가 Docker 컨테이너로 실행 중이었으나, 인프라 관리 에이전트로서 핵심 기능을 수행할 수 없었다:

- `qm list/status/reboot` — PVE Perl 모듈이 컨테이너에 없어 실패
- `systemctl` — libsystemd 공유 라이브러리 없어 실패
- `docker` — 소켓 미마운트로 실패

에이전트가 VM 관리, 서비스 재시작, 컨테이너 관리를 모두 못 하는 상태로, 역할 자체가 무력화됐다.

---

## 선택지

### A. Docker 유지 + 워크어라운드
- SSH to localhost (`ssh ksh@192.168.1.94`)로 qm/systemctl 우회
- Docker socket 마운트 (`/var/run/docker.sock`)
- PVE Perl 모듈 디렉토리 마운트

**기각 이유**: 워크어라운드가 쌓일수록 복잡도 증가. SSH to localhost는 키 관리 추가 부담. 근본 원인을 해결하지 않음.

### B. 네이티브 설치 (채택)
- 컨테이너에서 소스 추출 → 호스트 Python venv에 직접 설치
- systemd 서비스에서 `docker run` 제거
- `ksh` 계정으로 실행 (sudo NOPASSWD:ALL)

**채택 이유**: 호스트 직접 접근이 단순하고 확실. hermes-agent가 표준 Python 패키지라 설치 복잡도 낮음. Docker는 배포 편의를 위한 래퍼였을 뿐, 이 use case에서 이득 없음.

---

## 구현

```bash
# 소스 추출
sudo docker cp hermes:/opt/hermes/. /opt/hermes-agent/
sudo rm -rf /opt/hermes-agent/.venv /opt/hermes-agent/data

# 네이티브 venv 생성 및 설치
sudo python3 -m venv /opt/hermes-agent/.venv
sudo /opt/hermes-agent/.venv/bin/pip install -e "/opt/hermes-agent[messaging,cron,pty]"

# 데이터 소유권 이전 (uid 10000 → ksh)
sudo chown -R ksh:ksh /opt/hermes/data
```

systemd 서비스 (`hermes/hermes.service`):
```ini
[Service]
User=ksh
ExecStart=/opt/hermes-agent/.venv/bin/hermes gateway run
EnvironmentFile=/opt/hermes/.env
Environment=HERMES_HOME=/opt/hermes/data
```

---

## 결과

| 명령 | 이전 (Docker) | 이후 (네이티브) |
|------|--------------|----------------|
| `qm list` | ❌ Perl 모듈 없음 | ✅ sudo qm list |
| `systemctl` | ❌ libsystemd 없음 | ✅ sudo systemctl |
| `docker` | ❌ 소켓 없음 | ✅ sudo docker |
| `kubectl` | ✅ | ✅ |
| `ssh vm101` | ✅ | ✅ |

---

## 관련 변경

- `hermes/hermes.service`: docker run → 네이티브 hermes 실행
- `scripts/discord-dm.py`: container env → /opt/hermes/.env 파일 직접 읽기
- `scripts/hermes-notify`: `docker exec` 제거
