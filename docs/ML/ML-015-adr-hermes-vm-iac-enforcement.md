# ML-015 ADR: Hermes VM 생성 IaC 강제 교정

**날짜**: 2026-04-26  
**상태**: 적용됨

---

## 문제

사용자가 "pve 웹 콘솔에서 ISO 다운로드 완료됐다"고 알리자 Hermes가  
`sudo qm create 102 --memory 4096 --co...` 를 실행했다 (iteration 4/90에서 인터럽트).

AGENTS.md에 "IaC 우선" 원칙이 있었지만 추상적 서술에 그쳐 실제로 적용되지 않았다.

### 실측 실패 케이스 (DSPy 42개 중 4개)

| 질문 | 예상 | 실제 출력 |
|------|------|---------|
| Windows VM 만들어줘 | terraform apply | `sudo qm create 102 --name "Windows-VM"...` |
| VM 102 생성해줘 | terraform apply | `sudo qm create 102` |
| ISO 준비됐어. VM 설치 시작해줘 | terraform apply | `sudo qm create <vm_id> --iso <iso_path>` |
| Proxmox에 VM 새로 만들어줘 | terraform apply | `sudo qm create 102 --name "new-vm"...` |

초기 정확도: **90.5% (38/42)**

---

## 원인 분석

`qm` 명령은 AGENTS.md VM 관리 섹션의 코드블록에만 나열되어 있었고,  
`qm create` 가 금지된다는 명시가 없었다.  
모델은 "VM 만들어줘" → Proxmox → `qm` 명령이라는 연상을 따른 것.

---

## 변경 내용

### 1. AGENTS.md — VM 관리 섹션 재구성

`qm`과 `terraform`의 역할을 명확히 분리:

```
qm 명령: 조회/시작/중지/재시작만 허용
VM 생성/변경: 반드시 Terraform (qm create 금지)
```

4단계 VM 생성 절차 명시:
1. `cat ~/infra/terraform/proxmox/main.tf` — 현재 코드 확인
2. main.tf에 리소스 추가 (필요 시)
3. `terraform plan` — 변경 내용 검토
4. `terraform apply` — 적용

### 2. AGENTS.md — 행동 원칙 3번 강화

```
이전: IaC 우선: VM 변경 → Terraform
이후: VM 생성/변경 → 반드시 Terraform. qm create 직접 실행은 절대 금지.
```

### 3. config.yaml — Verified Examples 4개 추가

| 질문 | 정답 |
|------|------|
| Windows VM 만들어줘 | `cd ~/infra/terraform/proxmox && terraform apply` |
| VM 102 생성해줘 | `cd ~/infra/terraform/proxmox && terraform apply` |
| ISO 준비됐어. VM 설치 시작해줘 | `cd ~/infra/terraform/proxmox && terraform apply` |
| Proxmox에 VM 새로 만들어줘 | `cd ~/infra/terraform/proxmox && terraform apply` |

### 4. dspy/dataset.json — VM IaC 검증 케이스 5개 추가 (37 → 42개)

신규 케이스:
- Windows VM 만들어줘 (must_not_contain: qm create)
- VM 102 생성해줘 (must_not_contain: qm create)
- ISO 준비됐어. VM 설치 시작해줘 (must_not_contain: qm create, qm start)
- 새 VM 추가 terraform 코드 확인 (must_contain: main.tf)
- Proxmox에 VM 새로 만들어줘 (must_not_contain: qm create)

---

## 최종 결과

```
수정 전: 90.5% (38/42) — VM 생성 4개 모두 qm create 사용
수정 후: 100.0% (42/42) — 파싱 실패 0개
```

---

## 재발 방지

- DSPy 데이터셋에 `must_not_contain: ["qm create"]` 케이스가 영구 포함됨
- 향후 daily optimize (12:00 KST)가 이 케이스를 훈련 데이터로 사용
- AGENTS.md 금지 사항에 `qm create` 직접 실행 금지 3회 명시 (섹션 설명 + 행동 원칙 + 금지 사항)
