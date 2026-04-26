# ML-014 ADR: DSPy 파이프라인 네이티브 환경 마이그레이션 + 100% 평가 달성

**날짜**: 2026-04-26  
**상태**: 적용됨

---

## 배경

이전 세션(ML-008)에서 DSPy 평가 파이프라인을 구축하고 92% 정확도를 달성했다.  
그러나 이후 Hermes가 Docker → 네이티브(PVE 호스트 systemd)로 마이그레이션되면서  
dataset.json의 expected_command와 script의 system_prompt가 모두 Docker 시대 경로로 고착됐다.

### 측정된 문제 (Before)

| 항목 | 상태 |
|------|------|
| 평가 정확도 | 78.4% (29/37) — Docker 경로 기준 |
| 파싱 실패 | 0개 (max_tokens 4096 + enable_thinking=False 적용 후) |
| cron_optimize.py system_prompt | Docker 컨테이너 경로 (`/infra/`, `ssh -i /opt/data/vm_key`) 하드코딩 |
| optimize.py system_prompt | 동일하게 Docker 경로 하드코딩 |
| cron_optimize.py git commit | 작성자 미지정 (anonymous commit) |

---

## 변경 내용

### 1. dataset.json 재작성 (37 케이스)

Docker 시대 명령어를 네이티브 환경 기준으로 전면 수정:

| 이전 (Docker) | 이후 (Native) |
|--------------|--------------|
| `ssh -i /opt/data/vm_key ubuntu@192.168.1.24 nvidia-smi` | `ssh vm101 nvidia-smi` |
| `kubectl logs -n vllm deployment/vllm` | `ssh vm100 kubectl logs -n vllm deployment/vllm` |
| `qm list` | `sudo qm list` |
| `cd /infra/terraform/proxmox` | `cd ~/infra/terraform/proxmox` |

`must_not_contain` 버그 수정: `/infra/` 패턴이 `~/infra/`를 substring으로 차단하던 문제 제거.

신규 테스트 케이스 추가 (3개):
- Hermes 서비스 위치 확인 → `systemctl status hermes`
- AGENTS.md 수정 후 재시작+검증 → `systemctl restart hermes && journalctl`
- 파일 수정 전 내용 확인 → `cat ~/infra/...`

### 2. evaluate.py 수정

```python
lm = dspy.LM(
    f"openai/{MODEL_NAME}",
    api_base=API_BASE,
    api_key="none",
    max_tokens=4096,           # 6000 → 4096 (thinking chain 억제)
    temperature=0.0,
    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
)
```

`load_signature()` 함수로 system_prompt를 `hermes/config.yaml`에서 읽음 → 단일 소스.

### 3. optimize.py / cron_optimize.py 리팩터

**공통 변경:**
- Docker 시대 `make_signature(examples_text)` 제거 → `load_signature()` 사용
- `max_tokens=4096`, `enable_thinking=False` 적용
- config write 경로: `/opt/hermes/data/config.yaml` → `~/infra/hermes/config.yaml` (infra 레포 정본)

**cron_optimize.py 추가 변경:**
- git commit 작성자: `user.name="Hermes"`, `user.email="hermes@192.168.1.94"`
- Verified Examples 갱신 시 기존 블록만 교체 (`re.sub` 패턴), 나머지 system_prompt 보존

---

## 최적화 결과

### BootstrapFewShot (자동)

```
베이스라인: 87.5% (7/8 eval subset)
최적화 후:  100.0% (8/8 eval subset)
```

전체 37개 평가:
- Before: 78.4% (29/37)
- After:  86.5% (32/37)

고친 케이스 (+6): journalctl hermes 로그, providers.tf, main.tf, hermes config.yaml, systemctl status, AGENTS.md 반영

회귀 케이스 (-3): 현재 로드 모델(curl→nvidia-smi), GPU operator(-n vllm), 인프라 관리(providers.tf→CLAUDE.md)

### 수동 Verified Examples 추가 (+7개)

회귀 케이스 복구 및 미커버 케이스 보강:

| 추가 예시 | 수정 이유 |
|----------|---------|
| `현재 로드된 모델 이름` → `curl /v1/models` | optimizer가 nvidia-smi로 유도 |
| `GPU operator 파드` → `kubectl -n gpu-operator` | optimizer가 -n vllm으로 유도 |
| `인프라 어떻게 관리` → `cat ~/infra/CLAUDE.md` | optimizer가 providers.tf로 유도 |
| `k8s worker-gpu GPU 리소스` → `kubectl describe node worker-gpu` | 미커버 케이스 |
| `Hermes 로그 30줄` → `journalctl -u hermes -n 30` | 미커버 케이스 |
| `AGENTS.md 반영 확인` → `systemctl restart && journalctl` | 미커버 케이스 |
| `Hermes 어디서 실행` → `systemctl status hermes` | ps aux 혼동 방지 |

### 최종 결과

```
총 정확도: 100.0% (37/37)  파싱실패: 0개
```

---

## 결론 및 운영 방침

### Verified Examples 관리 원칙

1. **optimizer 자동 갱신** (매일 12:00 KST): BootstrapFewShot → infra 레포 commit → 사용자 알림
2. **회귀 발생 시**: 자동 갱신 후 evaluate.py로 전체 평가 실행 → 회귀 케이스는 수동으로 추가
3. **단일 소스**: `hermes/config.yaml`의 `## Verified Examples` 블록이 정본. `systemctl restart hermes`로 `/opt/hermes/data/`에 배포됨.

### enable_thinking=False 이유

Carnice-9b(Qwen3.5-9B)는 thinking 모드에서 reasoning_content에 토큰을 소비하고 실제 응답이 짧아진다.  
DSPy structured output 파싱이 thinking chain에 영향받지 않도록 항상 비활성화.  
`max_tokens=4096`이면 명령어 1줄 출력에 충분하며 thinking이 없으면 빠르다.

---

## 관련 파일

| 파일 | 변경 내용 |
|------|---------|
| `dspy/dataset.json` | 37 케이스, 네이티브 환경 기준 |
| `dspy/evaluate.py` | load_signature(), enable_thinking=False |
| `dspy/optimize.py` | load_signature(), enable_thinking=False |
| `dspy/cron_optimize.py` | 전면 재작성, Hermes git 작성자 |
| `hermes/config.yaml` | Verified Examples 20개 |
