# PVE-003: VM 102 Windows 테스트 VM (Terraform IaC)

**날짜**: 2026-04-26  
**상태**: Terraform 코드 작성 완료, ISO 다운로드 후 apply 예정

---

## 목표

Windows 11 테스트용 VM을 Terraform IaC로 관리한다.

---

## VM 사양

| 항목 | 값 |
|------|-----|
| VM ID | 102 |
| 이름 | windows-test |
| CPU | 4 cores (x86-64-v2-AES) |
| RAM | 8 GB |
| 디스크 | 60 GB (local-lvm, VirtIO SCSI) |
| BIOS | OVMF (UEFI) — Windows 11 필수 |
| TPM | v2.0 — Windows 11 필수 |
| Network | vmbr0, VirtIO |
| VGA | QXL |
| 자동 시작 | false (테스트 전용) |

---

## 사전 조건

```bash
# ISO 파일을 PVE 호스트에 업로드
# 경로: /var/lib/vz/template/iso/
ls /var/lib/vz/template/iso/
# 필요 파일:
# - Win11_25H2_Korean_x64_v2.iso  (~6.7GB, Windows 11 한국어)
# - virtio-win.iso                 (~754MB, VirtIO 드라이버)
```

---

## Terraform 리소스 (`terraform/proxmox/main.tf`)

```hcl
resource "proxmox_virtual_environment_vm" "windows_test" {
  name      = "windows-test"
  node_name = "pve"
  vm_id     = 102
  machine   = "q35"
  bios      = "ovmf"

  cpu    { cores = 4; sockets = 1; type = "x86-64-v2-AES" }
  memory { dedicated = 8192 }

  efi_disk  { datastore_id = "local-lvm"; type = "4m"; pre_enrolled_keys = false }
  tpm_state { datastore_id = "local-lvm"; version = "v2.0" }
  disk      { datastore_id = "local-lvm"; interface = "scsi0"; size = 60; iothread = true; discard = "on" }

  cdrom { interface = "ide2"; file_id = "local:iso/Win11_25H2_Korean_x64_v2.iso" }
  # VirtIO 드라이버: bpg/proxmox provider는 cdrom 1개 제한
  # apply 후 별도 추가: sudo qm set 102 --ide3 local:iso/virtio-win.iso,media=cdrom

  network_device { bridge = "vmbr0"; model = "virtio" }
  operating_system { type = "win11" }
  vga { type = "qxl" }

  boot_order    = ["ide2", "scsi0"]
  on_boot       = false
  started       = false
  scsi_hardware = "virtio-scsi-single"

  lifecycle { ignore_changes = [cdrom] }
}
```

---

## 배포 절차

```bash
# 1. ISO 확인
ls /var/lib/vz/template/iso/ | grep -E "Win11|virtio"

# 2. Terraform plan
cd ~/infra/terraform/proxmox && terraform plan

# 3. Terraform apply
terraform apply -auto-approve

# 4. VirtIO ISO 추가 (provider 제한으로 terraform 외부에서)
sudo qm set 102 --ide3 local:iso/virtio-win.iso,media=cdrom

# 5. VM 시작 (콘솔에서 설치)
sudo qm start 102
# PVE 웹 콘솔: https://192.168.1.94:8006 → VM 102 → Console

# 6. Windows 설치 중 VirtIO 드라이버 로드 (스토리지 인식용)
# "드라이버 로드" → D:\vioscsi\w11\amd64 선택
```

---

## 주의 사항

- `bpg/proxmox` provider는 `cdrom` 블록 1개만 허용 → VirtIO ISO는 `qm set`으로 별도 추가
- `on_boot = false`, `started = false` — 테스트 VM이므로 자동 시작 비활성
- Windows 설치 완료 후 ISO 제거: `sudo qm set 102 --delete ide2 --delete ide3`
- VM 삭제 시: `terraform destroy -target proxmox_virtual_environment_vm.windows_test`
