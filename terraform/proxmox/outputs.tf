output "worker_gpu_vm_id" {
  value = proxmox_virtual_environment_vm.worker_gpu.vm_id
}

output "worker_gpu_mac" {
  value = proxmox_virtual_environment_vm.worker_gpu.network_device[0].mac_address
}
