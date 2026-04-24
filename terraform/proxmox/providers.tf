terraform {
  required_providers {
    proxmox = {
      source  = "bpg/proxmox"
      version = "~> 0.78"
    }
  }
  required_version = ">= 1.0"
}

provider "proxmox" {
  endpoint  = var.proxmox_endpoint
  api_token = var.proxmox_api_token
  insecure  = true # 자체 서명 인증서
  ssh {
    agent            = false
    username         = "root"
    private_key      = file("~/.ssh/vm100_key")
  }
}
