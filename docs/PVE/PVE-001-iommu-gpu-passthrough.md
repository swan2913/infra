# PVE-001 · IOMMU 및 GPU PCIe 패스스루 설정

> 환경: Proxmox VE 9.1.1 / AMD Ryzen 5 5600X / RTX 3080 (PCI 06:00.0)  
> 완료일: 2026-04-25

## 목적
RTX 3080을 VM에 PCIe 패스스루하여 VM 내부에서 물리 GPU처럼 사용

## 사전 확인

```bash
# IOMMU 그룹 확인 (GPU가 독립 그룹에 있어야 함)
for d in /sys/kernel/iommu_groups/*/devices/*; do
  n=${d#*/iommu_groups/*}; n=${n%%/*}
  printf 'IOMMU Group %s ' "$n"
  lspci -nns "${d##*/}"
done | grep -i nvidia
# → IOMMU Group 16: 06:00.0 (RTX 3080), 06:00.1 (Audio)

# GPU PCI ID 확인
lspci -nn | grep -i nvidia
# → 10DE:2206 (VGA), 10DE:1AEF (Audio)
```

## Step 1 · GRUB IOMMU 활성화

```bash
sudo nano /etc/default/grub
# GRUB_CMDLINE_LINUX_DEFAULT 에 추가
# GRUB_CMDLINE_LINUX_DEFAULT="quiet nomodeset amd_iommu=on iommu=pt"

sudo update-grub
```

## Step 2 · VFIO 모듈 등록

```bash
sudo tee /etc/modules-load.d/vfio.conf << 'EOF'
vfio
vfio_iommu_type1
vfio_pci
EOF
```

## Step 3 · nouveau / nvidia 블랙리스트 (호스트 GPU 점유 방지)

```bash
sudo tee /etc/modprobe.d/blacklist-gpu.conf << 'EOF'
blacklist nouveau
blacklist nvidia
EOF
```

## Step 4 · vfio-pci에 RTX 3080 바인딩

```bash
sudo tee /etc/modprobe.d/vfio.conf << 'EOF'
options vfio-pci ids=10de:2206,10de:1aef
EOF

sudo update-initramfs -u -k all
```

## Step 5 · VM에 GPU 추가

```bash
# VM 100에 GPU passthrough 추가 (x-vga=0: 컴퓨팅 전용, 디스플레이 출력 없음)
sudo qm set 100 --hostpci0 0000:06:00,pcie=1,x-vga=0

sudo reboot
```

## Step 6 · 재부팅 후 확인

```bash
# 호스트: vfio-pci 바인딩 확인
lspci -k | grep -A3 "06:00"
# 기대값:
#   Kernel driver in use: vfio-pci

# IOMMU 활성화 확인
sudo dmesg | grep -i iommu | head -5
# 기대값:
#   iommu: Default domain type: Passthrough

# VFIO 모듈 로드 확인
lsmod | grep vfio
# 기대값: vfio, vfio_pci, vfio_iommu_type1 등
```

## 결과

| 항목 | 값 |
|------|-----|
| GPU PCI 주소 | 0000:06:00.0 |
| IOMMU 그룹 | 16 (독립) |
| 바인딩 드라이버 | vfio-pci |
| VM ID | 100 (이후 101로 이동 예정) |

## 참고
- `x-vga=0`: GPU를 디스플레이 어댑터가 아닌 컴퓨팅 장치로만 사용. ML 추론 목적에 적합.
- consumer GPU (GeForce)는 과거 VM 내 드라이버 오류 43 발생했으나, `nvidia-driver-*-open` (오픈 커널 모듈) 사용으로 해결됨.
