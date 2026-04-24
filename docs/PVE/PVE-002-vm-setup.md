# PVE-002 · VM 설정 및 SSH 접근 구성

> 환경: Proxmox VE 9.1.1 / VM 100 (ubuntu-1, 192.168.1.234)  
> 완료일: 2026-04-25

## VM 100 기본 스펙

| 항목 | 값 |
|------|-----|
| VM ID | 100 |
| 호스트명 | ubuntu-1 |
| OS | Ubuntu 24.04.4 LTS |
| CPU | 4코어 (KVM, x86-64-v2-AES) |
| RAM | 4GB |
| Disk | 64GB (local-lvm, LVM thin) |
| Network | vmbr0 (192.168.1.234/24, DHCP) |
| Machine | q35 |
| GPU | RTX 3080 PCIe Passthrough |

## VM 코어 증설 (1 → 4)

```bash
# PVE 호스트에서
sudo qm set 100 --cores 4
sudo qm reboot 100
sleep 20

# VM 내 확인
ssh vm100 nproc
# → 4
```

## PVE 호스트 → VM SSH 키 설정

```bash
# PVE 호스트에서
ssh-keygen -t ed25519 -f ~/.ssh/vm100_key -N ""

# VM에 공개키 등록
sshpass -p "비밀번호" ssh-copy-id \
  -i ~/.ssh/vm100_key.pub \
  -o StrictHostKeyChecking=no \
  ubuntu@192.168.1.234

# ~/.ssh/config 추가
cat >> ~/.ssh/config << 'EOF'

Host vm100
    HostName 192.168.1.234
    User ubuntu
    IdentityFile ~/.ssh/vm100_key
    StrictHostKeyChecking no
EOF

# 확인
ssh vm100 hostname
# → ubuntu-1
```

## GitHub SSH 키 설정 (PVE 호스트)

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github_key -N "" -C "ksh@pve-github"
cat ~/.ssh/github_key.pub
# → GitHub Settings → SSH keys 에 등록

cat >> ~/.ssh/config << 'EOF'

Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_key
    StrictHostKeyChecking no
EOF

ssh -T git@github.com
# → Hi swan2913! You've successfully authenticated...
```

## VM sudo NOPASSWD 설정

```bash
# VM에서
echo '비밀번호' | sudo -S bash -c \
  'echo "ubuntu ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/ubuntu \
   && chmod 440 /etc/sudoers.d/ubuntu'

# 확인
sudo whoami
# → root
```

## k3s kubeconfig 권한 설정

```bash
# VM에서
sudo mkdir -p /etc/rancher/k3s
sudo tee /etc/rancher/k3s/config.yaml << 'EOF'
write-kubeconfig-mode: "0644"
EOF

sudo systemctl restart k3s && sleep 10

# kubeconfig 사용자 홈으로 복사
cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
chmod 600 ~/.kube/config

kubectl get nodes
# → ubuntu-1  Ready  control-plane  v1.34.6+k3s1
```

## 현재 SSH config (PVE 호스트 ~/.ssh/config)

```
Host vm100
    HostName 192.168.1.234
    User ubuntu
    IdentityFile ~/.ssh/vm100_key
    StrictHostKeyChecking no

Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_key
    StrictHostKeyChecking no
```
