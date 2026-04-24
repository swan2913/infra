# infra — KAI Scheduler / GPU 추론 서버 GitOps

GitHub를 단일 원천으로 사용하는 GitOps 구조.  
ArgoCD가 이 리포를 감시하여 k3s 클러스터에 자동 반영.

---

## 아키텍처

```
[Proxmox VE 9.1.1 | 192.168.1.94]
  CPU : AMD Ryzen 5 5600X (6c/12t)
  RAM : 62GB
  GPU : NVIDIA RTX 3080 10GB (PCIe Passthrough → VM 100)
  SSD : NVMe 476GB

  └─ VM 100: ubuntu-1 (192.168.1.234)
       OS    : Ubuntu 24.04.4 LTS
       CPU   : 4코어 (KVM)
       RAM   : 4GB
       Disk  : 64GB (LVM thin)
       GPU   : RTX 3080 (PCIe Passthrough, 컴퓨팅 전용)
       k3s   : v1.34.6+k3s1 (Control Plane)
```

**GitOps 흐름**
```
git push → GitHub (swan2913/infra)
               ↓ ArgoCD 자동 감지 (1분 주기)
           k3s cluster (ubuntu-1)
               ├─ gpu-operator   (NVIDIA GPU Operator v26)
               └─ kai-scheduler  (v0.5.4)
```

---

## 접속 정보

| 시스템 | 방법 |
|--------|------|
| PVE 웹 UI | https://192.168.1.94:8006 |
| VM SSH | `ssh vm100` (PVE 호스트에서) |
| kubectl | `ssh vm100 kubectl ...` |
| ArgoCD UI | https://192.168.1.234:30443 (admin / 초기PW는 아래 참고) |

```bash
# ArgoCD 초기 비밀번호 확인
ssh vm100 kubectl get secret argocd-initial-admin-secret \
  -n argocd -o jsonpath='{.data.password}' | base64 -d && echo
```

---

## 디렉토리 구조

```
infra/
├── clusters/
│   └── ubuntu-1/
│       └── argocd-apps/          # ArgoCD Application 정의 (App-of-Apps)
│           ├── root.yaml          # 루트 앱 (이 디렉토리 전체 관리)
│           ├── gpu-operator.yaml
│           └── kai-scheduler.yaml
├── charts/
│   └── kai-scheduler/            # OCI 의존성 래퍼 차트
│       ├── Chart.yaml
│       ├── Chart.lock
│       └── values.yaml
├── ansible/
│   ├── inventory/hosts.ini       # 인벤토리
│   └── playbooks/
│       ├── setup-nvidia.yml      # NVIDIA 드라이버 + Container Toolkit
│       └── setup-k3s.yml         # k3s 설치
└── docs/
    └── architecture.md
```

---

## Phase별 구축 기록

### Phase 1 — Proxmox GPU 패스스루 (호스트에서 실행)

```bash
# 1) GRUB IOMMU 활성화
# /etc/default/grub 수정
# GRUB_CMDLINE_LINUX_DEFAULT="... amd_iommu=on iommu=pt"
sudo update-grub

# 2) VFIO 모듈 등록
sudo tee /etc/modules-load.d/vfio.conf <<'EOF'
vfio
vfio_iommu_type1
vfio_pci
EOF

# 3) nouveau 블랙리스트 (호스트가 GPU를 잡지 못하게)
sudo tee /etc/modprobe.d/blacklist-gpu.conf <<'EOF'
blacklist nouveau
blacklist nvidia
EOF

# 4) RTX 3080을 vfio-pci에 바인딩 (PCI ID: 10DE:2206 / 10DE:1AEF)
sudo tee /etc/modprobe.d/vfio.conf <<'EOF'
options vfio-pci ids=10de:2206,10de:1aef
EOF
sudo update-initramfs -u -k all

# 5) VM 100에 GPU 연결
sudo qm set 100 --hostpci0 0000:06:00,pcie=1,x-vga=0

# 재부팅 후 확인
sudo reboot
lspci -k | grep -A3 "06:00"
# → Kernel driver in use: vfio-pci

# 6) VM 코어 증설 (재부팅 필요)
sudo qm set 100 --cores 4
sudo qm reboot 100
```

### Phase 2 — VM 기본 설정 (PVE 호스트에서 실행)

```bash
# SSH 키 생성 및 VM에 등록
ssh-keygen -t ed25519 -f ~/.ssh/vm100_key -N ""
ssh-copy-id -i ~/.ssh/vm100_key.pub ubuntu@192.168.1.234

# ~/.ssh/config 추가
cat >> ~/.ssh/config <<'EOF'
Host vm100
    HostName 192.168.1.234
    User ubuntu
    IdentityFile ~/.ssh/vm100_key
    StrictHostKeyChecking no
EOF

# GitHub SSH 키 생성 (GitHub Settings → SSH keys 에 등록)
ssh-keygen -t ed25519 -f ~/.ssh/github_key -N "" -C "ksh@pve-github"
# cat ~/.ssh/github_key.pub 내용을 GitHub에 등록

cat >> ~/.ssh/config <<'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_key
    StrictHostKeyChecking no
EOF

# 연결 확인
ssh -T git@github.com
```

```bash
# VM: sudo 비밀번호 없이 설정
echo '비밀번호' | sudo -S bash -c \
  'echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu && chmod 440 /etc/sudoers.d/ubuntu'

# VM: k3s kubeconfig 권한 설정
sudo tee /etc/rancher/k3s/config.yaml <<'EOF'
write-kubeconfig-mode: "0644"
EOF
sudo systemctl restart k3s

cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
chmod 600 ~/.kube/config
```

### Phase 3 — NVIDIA 드라이버 + Container Toolkit (VM에서 실행)

```bash
# 빌드 도구
sudo apt-get update
sudo apt-get install -y linux-headers-$(uname -r) build-essential dkms ubuntu-drivers-common

# 권장 드라이버 확인 후 설치 (RTX 3080 → 580-open)
sudo ubuntu-drivers devices
sudo apt-get install -y nvidia-driver-580-open
sudo reboot

# 재부팅 후 확인
nvidia-smi
# → Driver 580.126.09 / CUDA 13.0 / 10240 MiB

# NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
```

### Phase 4 — k3s 설치 (VM에서 실행)

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC='server --disable traefik' sh -

# 확인
kubectl get nodes
# → ubuntu-1  Ready  control-plane  v1.34.6+k3s1
```

### Phase 5 — ArgoCD 설치 (VM에서 실행)

```bash
# ArgoCD 설치
kubectl create namespace argocd
kubectl apply -n argocd \
  -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml \
  --server-side --force-conflicts

# 배포 완료 대기
kubectl rollout status deployment/argocd-server -n argocd --timeout=120s

# UI NodePort 노출
kubectl patch svc argocd-server -n argocd \
  --type merge \
  -p '{"spec":{"type":"NodePort","ports":[{"name":"https","port":443,"targetPort":8080,"nodePort":30443}]}}'

# GitHub Deploy Key 생성 (GitHub → infra repo → Settings → Deploy keys 에 등록)
ssh-keygen -t ed25519 -f ~/.ssh/argocd_deploy_key -N "" -C "argocd@ubuntu-1"
cat ~/.ssh/argocd_deploy_key.pub

# ArgoCD에 GitHub 인증 Secret 등록
kubectl create secret generic argocd-repo-github \
  --namespace argocd \
  --from-literal=type=git \
  --from-literal=url=git@github.com:swan2913/infra.git \
  --from-file=sshPrivateKey=$HOME/.ssh/argocd_deploy_key
kubectl label secret argocd-repo-github -n argocd \
  argocd.argoproj.io/secret-type=repository

# Root App 적용 → 이후 GPU Operator, KAI Scheduler 자동 배포
kubectl apply -f - <<'EOF'
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: default
  source:
    repoURL: git@github.com:swan2913/infra.git
    targetRevision: main
    path: clusters/ubuntu-1/argocd-apps
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
EOF
```

---

## 현재 상태 (2026-04-25 기준)

| 항목 | 버전 / 상태 |
|------|------------|
| Proxmox VE | 9.1.1 |
| Ubuntu VM | 24.04.4 LTS |
| NVIDIA Driver | 580.126.09 |
| CUDA | 13.0 |
| GPU | RTX 3080 10GB (PCIe Passthrough) |
| k3s | v1.34.6+k3s1 |
| Helm | v3.20.2 |
| ArgoCD | stable (NodePort 30443) |
| GPU Operator | v26.3.1 (Synced) |
| KAI Scheduler | v0.5.4 (Synced) |

---

## 앱 배포 / 변경 방법

```bash
# PVE 호스트에서
cd ~/infra

# 앱 설정 변경 후
git add -A
git commit -m "feat: ..."
git push
# → ArgoCD가 1분 내 자동 감지하여 클러스터에 반영
```

## 클러스터 상태 확인

```bash
# 전체 앱 상태
ssh vm100 kubectl get app -n argocd -o wide

# GPU 사용 확인
ssh vm100 nvidia-smi

# GPU 리소스가 k8s에 노출됐는지 확인
ssh vm100 kubectl describe node ubuntu-1 | grep -A5 'nvidia.com'

# ArgoCD UI
# https://192.168.1.234:30443
```
