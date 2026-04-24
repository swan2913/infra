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

variable "proxmox_ssh_password" {
  description = "Proxmox root SSH password (for disk operations)"
  type        = string
  sensitive   = true
}

variable "vm_ssh_public_key" {
  description = "SSH public key injected via cloud-init"
  type        = string
}
