# ML-010 · ADR — Hermes 설정 파일 git 관리 구조

> 작성일: 2026-04-26  
> 상태: **채택**

## 결정

Hermes Agent의 `config.yaml`, `AGENTS.md`, `SOUL.md`를 `infra/hermes/`에서 git으로 관리하고,
서비스 기동 시 `ExecStartPre`가 `/opt/hermes/data/`로 복사하여 주입한다.

## 맥락

초기 구조에서는 Hermes 설정 파일이 `/opt/hermes/data/`에만 존재했다.

- system prompt를 수정하려면 PVE 호스트에서 직접 `sudo` 편집이 필요했다.
- 변경 이력이 git에 남지 않았다.
- `docs/ML/hermes-config.yaml.example`이 정본과 별개로 관리되어 실제 파일과 괴리가 생겼다.
- 관리 포인트가 `/opt/hermes/data/`와 `docs/ML/` 두 곳으로 분산되어 있었다.

## 선택지

### A. 직접 파일 bind mount
```
-v /home/ksh/infra/hermes/config.yaml:/opt/data/config.yaml
```
**문제**: 컨테이너 엔트리포인트가 `/opt/data` 전체에 `chown`을 실행하므로,
호스트 유저(ksh) 소유 파일에 대해 `Operation not permitted` 오류 발생.

### B. ExecStartPre 복사 (채택)
```ini
ExecStartPre=/bin/bash -c 'cp infra/hermes/config.yaml /opt/hermes/data/config.yaml && ...'
```
- git 정본: `infra/hermes/` (소유자: ksh, 일반 편집 가능)
- 운영 사본: `/opt/hermes/data/` (소유자: uid 10000, 컨테이너가 관리)
- `systemctl restart` 시 자동 동기화

**채택 이유**: 소유권 충돌 없음. git 워크플로 그대로 유지. 재시작 없이 반영되지 않는 것이 오히려 의도치 않은 핫패치를 방지하는 안전장치가 됨.

### C. 컨테이너 이미지 빌드
커스텀 Dockerfile로 설정을 이미지에 번들링.
**문제**: 설정 변경마다 이미지 재빌드·재배포 필요. 오버헤드가 지나치게 크다.

## 결과 구조

```
infra/
  hermes/
    config.yaml    ← system prompt, model 설정, Verified Examples (git 정본)
    AGENTS.md      ← 에이전트 행동 규칙 (git 정본)
    SOUL.md        ← 에이전트 정체성 (git 정본)

/opt/hermes/
  hermes.service   ← systemd 서비스 (ExecStartPre 복사 포함)
  data/
    config.yaml    ← 운영 사본 (재시작 시 덮어씌워짐, 직접 수정 금지)
    AGENTS.md      ← 운영 사본
    SOUL.md        ← 운영 사본
    .env           ← 민감 정보 (git 제외)
    vm_key         ← SSH 개인키 (git 제외)
    state.db       ← 런타임 상태 (git 제외)
```

## 설정 변경 워크플로

```bash
# 1. 수정
vi ~/infra/hermes/config.yaml

# 2. git commit & push
cd ~/infra && git add hermes/ && git commit -m "hermes: ..." && git push origin main

# 3. 반영 (ExecStartPre가 복사)
sudo systemctl restart hermes
```

## 포기한 관행

- `/opt/hermes/data/config.yaml` 직접 수정: 재시작 시 덮어씌워져 유실됨.
- `docs/ML/hermes-config.yaml.example` 별도 관리: `hermes/config.yaml`이 정본이므로 삭제.
