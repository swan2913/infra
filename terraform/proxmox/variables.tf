variable "proxmox_endpoint" {
  description = "Proxmox API endpoint"
  type        = string
  default     = "https://192.168.1.94:8006"
}

variable "proxmox_api_token" {
  description = "Proxmox API token (terraform@pve!terraform=<secret>)"
  type        = string
  sensitive   = true
}

# SSH는 키 인증으로 변경 (providers.tf 참고)
# proxmox_ssh_password 변수 제거됨

variable "vm_ssh_public_key" {
  description = "SSH public key injected via cloud-init"
  type        = string
}
