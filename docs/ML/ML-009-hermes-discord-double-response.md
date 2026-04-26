# ML-009 · Hermes Discord 이중 응답 회고록

> 작성일: 2026-04-25  
> 상태: **해결 완료**

---

## 증상

Discord DM으로 Hermes에게 메시지를 보내면 응답이 두 개 도착한다.  
두 응답의 내용이 서로 다르다 (단순 중복 전송이 아님).

---

## 추정

### 추정 1 — `interim_assistant_messages` 설정 문제
Hermes는 도구 실행 중 중간 메시지를 Discord에 전송하는 기능(`interim_assistant_messages`)이 있다.  
이 기능이 활성화된 상태에서 최종 응답까지 두 개의 메시지가 발송되는 것 아닐까?

### 추정 2 — 서비스 재시작 후 캐시 초기화
`MessageDeduplicator`가 TTL 기반 메모리 캐시를 사용하므로 `systemctl restart hermes` 시 캐시가 초기화된다.  
재시작 직전에 처리된 메시지 ID가 캐시에서 사라져 재처리되는 것 아닐까?

### 추정 3 — API 호출 중단 후 재시도
Hermes 로그에서 `⚡ Interrupted during API call` 메시지 확인.  
LLM API 호출이 중단되면 에이전트가 이전 턴을 재시도하면서 두 번째 응답이 생성되는 것 아닐까?

---

## 확인

### 추정 1 확인
`/opt/hermes/data/config.yaml`에 `display.interim_assistant_messages: false` 추가 후 재시작.  
→ 이중 응답 **지속됨**. 추정 1 기각.

### 추정 2 확인
Hermes 재시작 없이 DM 전송 테스트.  
→ 이중 응답 **지속됨**. 추정 2 기각.

### 추정 3 확인
`run.py` 내 interrupted 관련 코드 분석.  
→ `result.get("interrupted")` 플래그가 True일 때 System note를 컨텍스트에 주입하고 에이전트가 이어서 생성하는 경로 확인.  
→ 그러나 이 경로가 실제로 이중 응답을 유발하는지 직접 증명하려면 추가 분석 필요.

---

## 조치

추정 3을 기반으로 `run.py` 내 interrupted 재시도 경로를 추적하려 함.

```bash
grep -n "Interrupted\|interrupted\|resume_pending" /opt/hermes/gateway/run.py
```

→ 관련 라인: 10107, 10137, 10146, 10629, 10708

---

## 실패

`/opt/hermes/gateway/run.py` 경로로 파일 읽기 시도 → **파일 없음**.  
Hermes가 Docker 컨테이너 내에서 실행되고 있어 소스 파일이 호스트 파일시스템에 없었음.  
컨테이너 접근도 `docker` 명령 권한 문제(`/var/run/docker.sock` permission denied)로 막힘.  
→ interrupted 경로 분석을 통한 접근 **중단**.

---

## 재추론

소스 분석이 막힌 상황에서 방향을 전환하여 실행 중인 프로세스 자체를 확인.

```bash
sudo docker ps | grep hermes
```

---

## 원인

**Hermes 컨테이너가 두 개 동시에 실행 중이었다.**

| 컨테이너 | 이름 | 가동 시간 | 기동 방식 |
|---------|------|----------|----------|
| `9df20d082b20` | `hermes` | 11분 | systemd 서비스 |
| `7d84386f35be` | `clever_benz` | 6시간 | 수동 `docker run` |

두 컨테이너가 **동일한 Discord 봇 토큰**을 공유하며 각자 독립적으로 메시지를 수신하고 응답했다.  
응답 내용이 달랐던 이유는 각 컨테이너가 독립적인 LLM 호출을 통해 별개의 응답을 생성했기 때문이다.

`systemd` 서비스의 `ExecStartPre`는 `docker stop hermes` / `docker rm hermes`만 실행한다.  
`clever_benz`는 이름이 달라 `ExecStartPre`에 걸리지 않았고, 재시작을 거듭해도 살아남았다.

---

## 해결

```bash
sudo docker stop clever_benz && sudo docker rm clever_benz
```

이후 `hermes` 컨테이너 단독 실행 상태에서 DM 테스트 → 응답 **1회**만 도착, 정상 확인.

### 재발 방지

`hermes.service`의 `ExecStartPre`에 이름과 무관하게 동일 토큰 컨테이너를 정리하는 방어 로직 추가를 고려할 수 있다.  
또는 Docker 컨테이너 이름 규칙을 `--name hermes`로 고정하고 수동 `docker run` 시 반드시 `--name hermes`를 지정하도록 운영 규칙화.

---

## 교훈

> 코드보다 먼저 프로세스를 확인하라.

이중 응답이라는 증상에서 자연스럽게 코드 버그(캐시, 재시도 로직)를 의심했으나,  
실제 원인은 동일 프로세스가 두 번 실행되는 운영 환경 문제였다.  
`docker ps` 한 줄이 수백 줄의 소스 분석보다 빨랐다.
