# GPU-001 · NVIDIA 드라이버 및 Container Toolkit 설치 (VM 내)

> 환경: Ubuntu 24.04.4 LTS / RTX 3080 (PCIe Passthrough)  
> 완료일: 2026-04-25

## 전제 조건
- PVE-001 완료 (vfio-pci 바인딩)
- VM 내에서 `lspci | grep -i nvidia` 로 GPU 인식 확인

## GPU 인식 확인

```bash
lspci | grep -i nvidia
# → 01:00.0 VGA compatible controller: NVIDIA Corporation GA102 [GeForce RTX 3080]
# → 01:00.1 Audio device: NVIDIA Corporation GA102 High Definition Audio Controller
```

## Step 1 · 빌드 도구 설치

```bash
sudo apt-get update
sudo apt-get install -y \
  linux-headers-$(uname -r) \
  build-essential \
  dkms \
  ubuntu-drivers-common
```

## Step 2 · 권장 드라이버 확인

```bash
sudo ubuntu-drivers devices
# → driver : nvidia-driver-580-open - distro non-free recommended
```

## Step 3 · 드라이버 설치 및 재부팅

```bash
sudo apt-get install -y nvidia-driver-580-open
sudo reboot
```

## Step 4 · 설치 확인

```bash
nvidia-smi
```

기대 출력:
```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.126.09   Driver Version: 580.126.09   CUDA Version: 13.0               |
| GPU  Name            | RTX 3080 | 10240 MiB |
```

## Step 5 · NVIDIA Container Toolkit 설치

```bash
# GPG 키 등록
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# 저장소 추가
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 설치
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
nvidia-ctk --version
# → NVIDIA Container Toolkit CLI version 1.19.0
```

## 결과

| 항목 | 값 |
|------|-----|
| 드라이버 버전 | 580.126.09 |
| CUDA 버전 | 13.0 |
| VRAM | 10240 MiB |
| Container Toolkit | 1.19.0 |

## 주의사항
- `nvidia-driver-580-open` (오픈 커널 모듈): consumer GPU의 VM 내 드라이버 오류 43 없음
- `x-vga=0` passthrough이므로 VM 내 디스플레이 출력 없음, `nvidia-smi`로만 확인
