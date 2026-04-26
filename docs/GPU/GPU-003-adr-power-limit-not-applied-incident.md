# GPU-003 · 인시던트: RTX 3080 Power Limit 미적용 원인 분석 및 대응

> 작성일: 2026-04-26  
> 환경: worker-gpu (VM 101, 192.168.1.24) / RTX 3080 / Ubuntu 24.04

---

## 발견 경위

정기 서버 상태 점검 중 `nvidia-smi` 출력값을 확인했을 때 다음이 눈에 띄었다.

```
power.limit = 370.00 W
```

`docs/CHECKLIST.md`에는 이미 완료 체크가 되어 있었다.

```
- [x] GPU-002 · RTX 3080 Power Limit 최적화 — 250W (실측: 성능 93%, 전력 78%, W/tok 최저)
```

"완료"로 기록된 항목과 실제 시스템 상태가 불일치했다. 이 간극이 조사의 출발점이다.

---

## 원인 추론 과정

### 1단계 — 현상 확인

`nvidia-smi` 전체 쿼리로 Power Limit 관련 수치를 확인했다.

```
Current Power Limit  : 370.00 W
Requested Power Limit: 370.00 W
Default Power Limit  : 370.00 W
```

Requested(요청값)까지 370W였다. 단순 일시적 초기화가 아니라 **설정 자체가 없는 상태**임을 의미한다. 재부팅 후 초기화됐다면 Current만 기본값으로 돌아갔을 것이고, 어떤 서비스가 설정을 시도했다면 Requested가 250W로 남아있어야 한다.

### 2단계 — 서비스 존재 여부 확인

Ansible playbook(`setup-nvidia-powerlimit.yml`)은 `nvidia-powerlimit.service`를 systemd에 등록해 재부팅 후에도 250W를 유지하도록 설계되어 있다. 서비스 상태를 먼저 확인했다.

```bash
systemctl is-active nvidia-powerlimit.service
# → inactive

systemctl list-units --state=failed
# → 0 loaded units listed
```

`inactive`이면서 failed 목록에도 없다 — **서비스 유닛 자체가 존재하지 않는 상태**다. failed였다면 "설치는 됐지만 실행 중 오류"이나, 그조차 아니었다.

### 3단계 — 왜 미설치인가

VM 101(worker-gpu)의 구성 이력을 역추적했다. Ansible playbook 실행 순서는 다음과 같이 설계되어 있다.

```
1. setup-nvidia.yml          ← 드라이버 + Container Toolkit
2. setup-nvidia-powerlimit.yml ← Power Limit 설정 (별도 playbook)
3. setup-k3s-agent.yml       ← k3s worker 조인
```

`IaC-002-ansible-playbooks.md` 문서를 보면 VM 101 구성 당시 `setup-nvidia-powerlimit.yml`이 playbook 목록에 **주석으로 비활성화된 채** 기록되어 있었다(`worker-gpu` IP가 `192.168.1.xxx`로 미확정 상태).

```ini
# 이전 상태의 hosts.ini
[workers]
# worker-gpu ansible_host=192.168.1.xxx ...   ← IP 미정으로 주석 처리
```

**결론**: VM 101 IP가 확정(192.168.1.24)되기 전에 드라이버 설치까지는 수동으로 진행했으나, Power Limit playbook은 inventory 정비 전에 건너뛰어진 채 체크리스트만 완료로 표기됐다. 이후 inventory가 확정됐을 때 playbook 재실행 없이 문서만 갱신된 것으로 추정된다.

---

## 원인 요약

| 항목 | 내용 |
|------|------|
| 직접 원인 | `nvidia-powerlimit.service` systemd 유닛 미설치 |
| 근본 원인 | VM 101 IP 미확정 시점에 Power Limit playbook 실행이 누락됐고, 이후 체크리스트만 완료로 마킹됨 |
| 기여 요인 | 체크리스트 항목이 "설계 완료"와 "적용 완료"를 구분하지 않음 |

---

## 조치

Ansible playbook을 실행했다. 사전 검증 없이 바로 적용한 이유는 idempotent playbook이므로 재실행 부작용이 없기 때문이다.

```bash
cd ~/infra
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-nvidia-powerlimit.yml
```

**실행 결과:**

```
TASK [nvidia-powerlimit systemd 유닛 배포]        changed
TASK [nvidia-powerlimit 서비스 활성화 및 즉시 적용] changed
TASK [GPU 상태 출력]
  "NVIDIA GeForce RTX 3080, 250.00 W, 31.86 W, 44"
```

`changed` 항목이 2개(유닛 배포 + 서비스 등록)였다 — 예상대로 해당 설정이 없었음이 확인됐다.

---

## 결과 확인

Ansible 내장 검증 태스크(`nvidia-smi` 쿼리)가 `250.00 W`를 반환했다. 추가로 서비스 영속성을 확인했다.

```bash
systemctl is-active nvidia-powerlimit.service
# → active

systemctl is-enabled nvidia-powerlimit.service
# → enabled
```

`enabled` — 재부팅 후에도 자동 실행된다.

**조치 전후 비교:**

| 항목 | 조치 전 | 조치 후 |
|------|--------|--------|
| Power Limit | 370W (기본값) | **250W** |
| 서비스 상태 | 미설치 | active + enabled |
| GPU 온도 (idle) | 64°C | 44°C |
| GPU 소비전력 (idle) | 127W | 31.86W |

온도와 idle 소비전력의 차이는 Power Limit 자체 효과가 아니라 llama.cpp 추론 부하 유무의 차이다. Power Limit 변경의 실질 효과는 부하 상태에서 측정해야 하며, 벤치마크 결과는 `GPU-002`에 기록되어 있다.

---

## 앞으로 어떻게 해야 하나

### 규칙 1 — 체크리스트 항목은 실제 적용 시점에만 체크

설계·작성 완료와 시스템 적용 완료는 다르다. Ansible playbook 작성이 완료됐더라도 해당 노드에서 실제 실행하기 전까지는 체크하지 않는다.

### 규칙 2 — IP 미확정 노드의 playbook은 별도 표기

```markdown
- [ ] IaC-002 · setup-nvidia-powerlimit.yml — ⏳ worker-gpu IP 확정 후 실행 필요
```

"미실행 사유"를 인라인으로 명시하면 나중에 상태를 재확인할 수 있다.

### 규칙 3 — 상태 점검 시 Power Limit 포함

```bash
# 작업 전 체크 (CLAUDE.md 기재)
ssh worker-gpu nvidia-smi --query-gpu=power.limit --format=csv,noheader
```

현재 `CLAUDE.md`의 "작업 전 체크" 섹션에 포함되어 있지 않다. 추가를 권장한다.
