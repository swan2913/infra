# PVE 도메인 에이전트 규칙

## 담당 범위
Proxmox VE 호스트 설정, VM 생성/수정/삭제, 스토리지, 네트워크.

## 작업 원칙

- VM 변경(`qm set`) 전 반드시 현재 설정 확인: `sudo qm config <vmid>`
- 실행 중 VM에 hostpci 추가/삭제 불가 → 정지 후 작업
- GPU passthrough 변경 순서: VM 정지 → 설정 변경 → VM 시작 → 드라이버 확인
- Terraform이 관리하는 VM은 `qm` 직접 수정 금지 (state drift 발생)

## 주요 명령어 패턴

```bash
sudo qm list                         # VM 목록
sudo qm status <vmid>                # VM 상태
sudo qm config <vmid>                # VM 설정 확인
sudo qm set <vmid> --cores 4         # 설정 변경 (정지 상태 권장)
sudo qm start/stop/reboot <vmid>     # 전원 관리
lspci -k | grep -A3 "06:00"          # GPU 드라이버 바인딩 확인
```

## 파일 위치
- VM 정의: `terraform/proxmox/main.tf`
- GPU 패스스루 문서: `docs/PVE/PVE-001-iommu-gpu-passthrough.md`
- VM 설정 문서: `docs/PVE/PVE-002-vm-setup.md`
