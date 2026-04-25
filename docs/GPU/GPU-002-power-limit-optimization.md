# GPU-002 · RTX 3080 Power Limit 최적화

> 환경: Ubuntu 24.04 / RTX 3080 Gigabyte (max 370W) / llama.cpp 추론  
> 완료일: 2026-04-25

## 배경

Linux에서 NVIDIA GPU 언더볼팅은 불가능하다 (NVIDIA가 Kepler 이후 드라이버에서 전압 제어 API 제거).
Windows MSI Afterburner 방식의 전압 커브 조정은 미지원. `nvidia-smi -pl`을 통한 power limit이 유일한 실용적 방법.

## 벤치마크 결과

프롬프트: transformer vs RNN 비교 설명 (300 tokens 생성, 3회 평균)

| Power Limit | tok/s | 실소비W | core°C | W/tok | 성능비 |
|-------------|-------|---------|--------|-------|--------|
| 370W (기본) | 78.8 | 307W | 62°C | 3.90 | 100% |
| **250W** | **73.4** | **240W** | **59°C** | **3.26** | **93%** |
| 220W | 61.3 | 203W | 56°C | 3.31 | 78% |
| 200W | 50.4 | 196W | 56°C | 3.88 | 64% |

**최적점: 250W** — 성능 93% 유지, 전력 22% 절감, W/tok 최저

## 분석

- llama.cpp 추론은 VRAM 대역폭 병목이라 GPU 코어 클럭 여유가 있음
- 250W → 220W 구간에서 성능이 급격히 꺾임 (clock이 실제로 throttle 시작)
- 200W는 성능 손실 대비 전력 절감 폭이 작아 비효율

## hotspot 온도 비고

Gigabyte RTX 3080 (AIB 카드)는 `nvidia-smi`로 hotspot/junction 온도를 노출하지 않음.
Founders Edition 전용 기능. `Memory Current Temp` 도 N/A.
core 온도만 모니터링 가능.

## 적용 방법

```bash
# Ansible playbook 실행 (worker-gpu 대상)
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-nvidia-powerlimit.yml

# power limit만 변경할 때
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-nvidia-powerlimit.yml \
  -e nvidia_power_limit=220
```

systemd 서비스(`nvidia-powerlimit.service`)로 재부팅 후에도 자동 적용.
Persistence Mode(`-pm 1`)도 함께 설정되어 드라이버 상시 로드 유지.

## 관련 파일

- Ansible playbook: `ansible/playbooks/setup-nvidia-powerlimit.yml`
