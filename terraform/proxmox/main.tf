# Ubuntu 24.04 cloud image를 Proxmox에 등록
resource "proxmox_virtual_environment_download_file" "ubuntu_cloud_image" {
  content_type = "iso"
  datastore_id = "local"
  node_name    = "pve"
  url          = "https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
  file_name    = "ubuntu-24.04-cloud.img"
  overwrite    = false
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

  # GPU PCIe Passthrough (RTX 3080)
  hostpci {
    device  = "hostpci0"
    id      = "0000:06:00"
    pcie    = true
    rom_bar = true
  }

  disk {
    datastore_id = "local-lvm"
    file_id      = proxmox_virtual_environment_download_file.ubuntu_cloud_image.id
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

  on_boot  = true
  started  = true
  scsi_hardware = "virtio-scsi-single"
}
