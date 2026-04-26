# Ubuntu cloud image (VM 100/101 용)
data "proxmox_virtual_environment_file" "ubuntu_cloud_image" {
  content_type = "iso"
  datastore_id = "local"
  node_name    = "pve"
  file_name    = "ubuntu-24.04-cloud.img"
}

# VM 100 — k3s Control Plane (ArgoCD, kubectl 진입점)
resource "proxmox_virtual_environment_vm" "control_plane" {
  name      = "ubuntu-1"
  node_name = "pve"
  vm_id     = 100

  machine = "q35"

  cpu {
    cores   = 4
    sockets = 1
    type    = "x86-64-v2-AES"
  }

  memory {
    dedicated = 4096
  }

  disk {
    datastore_id = "local-lvm"
    interface    = "scsi0"
    size         = 64
    iothread     = true
    replicate    = false
  }

  network_device {
    bridge      = "vmbr0"
    model       = "virtio"
    mac_address = "BC:24:11:1F:AD:17"
    firewall    = true
  }

  operating_system {
    type = "l26"
  }

  vga {
    type = "virtio"
  }

  boot_order    = ["scsi0", "ide2", "net0"]
  on_boot       = true
  started       = true
  scsi_hardware = "virtio-scsi-single"

  # ISO 설치된 기존 VM — 디스크 재생성 방지
  lifecycle {
    ignore_changes = [
      disk[0].file_id,
      disk[0].file_format,
      memory[0].dedicated, # PVE 내부 반올림(4096→4196) 허용
    ]
  }
}

# VM 101 — k3s Worker + GPU 추론 노드
resource "proxmox_virtual_environment_vm" "worker_gpu" {
  name      = "worker-gpu"
  node_name = "pve"
  vm_id     = 101

  machine = "q35"
  bios    = "ovmf"

  cpu {
    cores   = 8
    sockets = 1
    type    = "x86-64-v2-AES"
  }

  memory {
    dedicated = 16384 # 16GB (vLLM 추론에 여유 필요)
  }

  # GPU PCIe Passthrough — Proxmox resource mapping "rtx3080" 사용
  hostpci {
    device  = "hostpci0"
    mapping = "rtx3080"
    pcie    = true
    rombar  = true
  }

  disk {
    datastore_id = "local-lvm"
    file_id      = data.proxmox_virtual_environment_file.ubuntu_cloud_image.id
    interface    = "scsi0"
    size         = 64
    iothread     = true
    discard      = "on"
  }

  efi_disk {
    datastore_id = "local-lvm"
    type         = "4m"
  }

  network_device {
    bridge = "vmbr0"
    model  = "virtio"
  }

  # cloud-init
  initialization {
    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }
    user_account {
      username = "ubuntu"
      keys     = [var.vm_ssh_public_key]
    }
  }

  operating_system {
    type = "l26"
  }

  vga {
    type = "virtio"
  }

  on_boot       = true
  started       = true
  scsi_hardware = "virtio-scsi-single"
}

# VM 102 — Windows 테스트 VM
# 사전 조건: Windows ISO를 /var/lib/vz/template/iso/windows.iso 에 업로드
# VirtIO 드라이버 ISO: /var/lib/vz/template/iso/virtio-win.iso (자동 다운로드)
resource "proxmox_virtual_environment_vm" "windows_test" {
  name      = "windows-test"
  node_name = "pve"
  vm_id     = 102

  machine = "q35"
  bios    = "ovmf" # UEFI — Windows 11 필수

  cpu {
    cores   = 4
    sockets = 1
    type    = "host"
  }

  memory {
    dedicated = 8192 # 8GB
  }

  # EFI 디스크 (OVMF UEFI 필수)
  efi_disk {
    datastore_id      = "local-lvm"
    type              = "4m"
    pre_enrolled_keys = false
  }

  # TPM (Windows 11 필수)
  tpm_state {
    datastore_id = "local-lvm"
    version      = "v2.0"
  }

  # 시스템 디스크 — VirtIO Block (Windows 설치 중 VirtIO 드라이버 필요)
  disk {
    datastore_id = "local-lvm"
    interface    = "virtio0"
    size         = 60
    backup       = false
  }

  # Windows 11 ISO (한국어, 25H2)
  cdrom {
    interface = "ide2"
    file_id   = "local:iso/Win11_25H2_Korean_x64_v2.iso"
  }
  # VirtIO 드라이버 ISO: bpg/proxmox cdrom 단일 제한으로 apply 후 별도 추가
  # sudo qm set 102 --ide3 local:iso/virtio-win.iso,media=cdrom

  network_device {
    bridge = "vmbr0"
    model  = "virtio"
  }

  operating_system {
    type = "win11"
  }

  vga {
    type = "virtio"
  }

  boot_order = ["ide2", "virtio0"]
  on_boot    = false
  started    = false

  lifecycle {
    # ISO를 꺼도 상태 변경이 발생하지 않도록
    ignore_changes = [cdrom]
  }
}
