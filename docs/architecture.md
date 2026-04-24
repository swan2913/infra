# KAI Scheduler 인프라 구성

## 아키텍처

```
[Proxmox Host 192.168.1.94]  (AMD Ryzen 5 5600X / 62GB RAM / RTX 3080)
  │
  └─ VM 100: ubuntu-1 (192.168.1.234)
       - Ubuntu 24.04, 4코어, 4GB RAM, 64GB NVMe
       - RTX 3080 PCIe Passthrough (10GB VRAM)
       - k3s v1.34 Control Plane
       - NVIDIA Driver 580 + Container Toolkit
       │
  [Switch 192.168.1.0/24]
       │
  ├─ Worker 1 (예정)
  └─ Worker 2 (예정)
```

## 접속 정보

| 시스템 | 접속 방법 |
|--------|-----------|
| PVE 웹UI | https://192.168.1.94:8006 |
| VM 100 SSH | `ssh vm100` |
| kubectl | `ssh vm100 sudo k3s kubectl ...` |

## 구축 단계

- [x] Phase 1: IOMMU + vfio-pci GPU 패스스루
- [x] Phase 2: VM 설정 (코어, SSH, sudo)
- [x] Phase 3: NVIDIA Driver 580 + Container Toolkit
- [x] Phase 4: k3s v1.34 설치
- [ ] Phase 5: NVIDIA GPU Operator
- [ ] Phase 6: KAI Scheduler
- [ ] Phase 7: IaC 완성 (Terraform + Ansible)
