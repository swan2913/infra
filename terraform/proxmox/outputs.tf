output "control_plane_vm_id" {
  value = proxmox_virtual_environment_vm.control_plane.vm_id
}

output "control_plane_mac" {
  value = proxmox_virtual_environment_vm.control_plane.network_device[0].mac_address
}

output "worker_gpu_vm_id" {
  value = proxmox_virtual_environment_vm.worker_gpu.vm_id
}

output "worker_gpu_mac" {
  value = proxmox_virtual_environment_vm.worker_gpu.network_device[0].mac_address
}
