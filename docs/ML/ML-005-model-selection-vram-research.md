# ML-005 · 모델 선택 및 VRAM 최적화 리서치

> 작성일: 2026-04-25

## 개요

Hermes Agent 백엔드 모델 선택과 RTX 3080(10GB VRAM) 환경에서의 VRAM 최적화 방향을 분석한 리서치 기록.

---

## 1. 모델 선택

### 요구사항
- RTX 3080 10GB VRAM
- Hermes Agent 프레임워크 호환
- tool calling 신뢰성
- 인프라 모니터링 에이전트 (k8s 상태 관리, 보고)

### 후보 비교

| 모델 | 기반 | VRAM (Q4_K_M) | tool calling | Hermes 호환 | 컨텍스트 |
|------|------|--------------|-------------|------------|--------|
| **kai-os/Carnice-9b** | Qwen3.5-9B | ~6GB | ★★★★★ | ★★★★★ (전용 튜닝) | 262K |
| NousResearch/Hermes-3-Llama-3.1-8B | Llama 3.1 8B | ~5GB | ★★★★ | ★★★★★ (공식) | 32K |
| Qwen3.5-9B (base) | - | ~6GB | ★★★★★ | ★★★ | 262K |
| ykarout/Qwen3.5-9b-Opus-Openclaw-Distilled | Qwen3.5-9B | ~6GB | ★★★★ | ★★★ | 262K |

### 선택: kai-os/Carnice-9b

**이유:**
- Hermes Agent harness 전용 2단계 학습 (Stage A: reasoning repair, Stage B: Hermes 트레이스)
- Hermes-3 공식 모델(32K) 대비 컨텍스트 8배 (262K)
- 커뮤니티: "Qwen3.5가 60%만 성공하던 tool call을 Carnice는 확실히 해냄"
- 코딩 벤치마크 데이터 없음 — 인프라 에이전트 전용으로 설계된 모델

**코딩 서브에이전트 한계:** Hermes 신뢰성을 위해 범용 코딩 능력 일부 희생. 코딩은 클라우드 FM 담당.

---

## 2. 컨텍스트 윈도우 분석

### 모델 스펙 vs 실효 한계

| 범위 | 품질 | 비고 |
|------|------|------|
| ~32K | ★★★★★ | 완전 신뢰 |
| 32K~64K | ★★★★ | 실용적 상한선 |
| 64K~131K | ★★★ | GDN 하이브리드 덕분에 버티나 정밀 검색 약화 |
| 131K+ | ★★ | 이론상 가능, 실사용 품질 저하 |

**Qwen3.5-9B의 262K 지원은 이론치.** GDN(Gated DeltaNet) + 풀어텐션 교차 구조 덕분에 일반 9B보다 길게 버티지만, 실효 상한은 ~64K.

### 현재 설정

```
--ctx-size 131072  →  슬롯당 65,536 tokens × 2슬롯
```

실효 상한(64K)과 일치. **최적 설정 유지.**

---

## 3. 양자화 분석

### Carnice-9b GGUF 제공 파일

| 파일 | 크기 | 예상 총 VRAM | 판정 |
|------|------|------------|------|
| Q4_K_M | 5.63 GB | 6,917 MiB | 이전 설정 |
| **Q6_K** | 7.36 GB | ~8,669 MiB | **채택** |
| Q8_0 | 9.53 GB | ~10,860 MiB | KV 캐시 포함 초과 |

Q5_K_M은 미제공.

### Q4_K_M → Q6_K 효과

- Perplexity 손실: +0.0535 → ~+0.020 (약 34% 감소)
- 코딩/추론 태스크에서 벤치마크 유의미한 차이
- 실측 VRAM: Q4_K_M 6,917 MiB → Q6_K 8,339 MiB (+1,422 MiB)

---

## 4. VRAM 최적화 분석

### 현재 상태 (Q6_K 기준)

```
사용: 8,339 MiB / 10,240 MiB
여유: 1,537 MiB (~1.5GB)
```

### GDN 하이브리드 아키텍처 특성

Carnice-9b는 순수 트랜스포머가 아님:

```
총 40개 레이어
  ├── 8개: 풀어텐션 → KV 캐시 (Q4_0, 1,152 MiB)
  └── 32개: GDN 순환  → 상태 메모리 (f32, 100.5 MiB, 최고 정밀도)
```

### KV cache 업그레이드 (Q4_0 → Q8_0) — 보류

- 8개 레이어에만 적용 → 순수 트랜스포머보다 효과 제한적
- +1,152 MiB 대비 효과 불충분
- **채택 안 함**

### Speculative decoding — 불가

- Qwen3.5 계열 consumer GPU 테스트: 속도 3~12% **저하**
- GDN 순환 레이어가 토큰 검증 병렬화 방해
- llama.cpp hybrid SSM spec decoding 버그 이력 (PR #20075)
- **채택 안 함**

### Embedding 모델 추가 — 불필요

- 임베딩은 실시간성 낮아 CPU 충분
- VRAM 낭비
- **채택 안 함**

### Parallel 슬롯 증가 — 보류

Discord 단일 유저 환경에서는 불필요하나, **멀티유저 서버 초대 시 유의미**.

| parallel | 추가 VRAM | 총 사용 | 여유 |
|----------|----------|--------|------|
| 2 (현재) | - | 8,339 MiB | 1,537 MiB |
| 3 | +576 MiB | 8,915 MiB | 1,325 MiB |
| **4** | +1,152 MiB | **9,491 MiB** | **749 MiB** |
| 5 | +1,728 MiB | 10,067 MiB | 173 MiB ❌ |

**최대 parallel 4까지 안전.** Discord 멀티유저 서버 초대 시 함께 적용 예정.

추가 변경 필요 사항:
- `charts/vllm/values.yaml`: `--parallel 4`
- `charts/hermes/`: `DISCORD_ALLOWED_USERS` 확장 (현재 단일 유저 고정)

---

## 5. 결론 및 현재 적용 설정

```
모델:    Carnice-9b-Q6_K.gguf
엔진:    llama.cpp server-cuda (v8914)
GPU:     RTX 3080 전 레이어 적재
ctx:     131072 (슬롯당 65,536 × 2슬롯)
KV:      Q4_0 (GDN 구조상 업그레이드 효과 미미)
Flash:   on
VRAM:    8,339 / 10,240 MiB (여유 1,537 MiB — 버퍼)
```

## 6. 보류 항목

- [ ] Discord 멀티유저 서버 초대 시: `--parallel 4` + `DISCORD_ALLOWED_USERS` 확장
