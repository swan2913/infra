# IaC-001 · Terraform으로 Proxmox VM 관리

> Provider: bpg/proxmox ~0.78 / Terraform 1.14.9  
> 완료일: 2026-04-25

## Proxmox API 토큰 생성

```bash
# PVE 호스트에서
sudo pveum user add terraform@pve --comment "Terraform IaC"

sudo pveum role add TerraformRole --privs \
  "Datastore.AllocateSpace,Datastore.Audit,Pool.Allocate,\
Sys.Audit,Sys.Console,Sys.Modify,VM.Allocate,VM.Audit,VM.Clone,\
VM.Config.CDROM,VM.Config.CPU,VM.Config.Cloudinit,VM.Config.Disk,\
VM.Config.HWType,VM.Config.Memory,VM.Config.Network,VM.Config.Options,\
VM.Migrate,VM.PowerMgmt,SDN.Use"

sudo pveum aclmod / -user terraform@pve -role TerraformRole
sudo pveum user token add terraform@pve terraform --privsep=0
# Token: terraform@pve!terraform = <uuid>
```

## Terraform 설치 (Debian Trixie — apt 미지원, 바이너리 설치)

```bash
TF_VER="1.14.9"
wget -q "https://releases.hashicorp.com/terraform/${TF_VER}/terraform_${TF_VER}_linux_amd64.zip" \
  -O /tmp/terraform.zip
sudo apt-get install -y unzip
sudo unzip -o /tmp/terraform.zip -d /usr/local/bin/
terraform version
# → Terraform v1.14.9
```

## 디렉토리 구조

```
terraform/proxmox/
├── providers.tf          # bpg/proxmox provider 설정
├── variables.tf          # 입력 변수 정의
├── main.tf               # VM 리소스 정의
├── outputs.tf            # VM ID, MAC 출력
└── terraform.tfvars.example  # 예시 (실제 tfvars는 .gitignore)
```

## 사용법

```bash
cd ~/infra/terraform/proxmox

# 1) tfvars 파일 생성 (git에 올리지 않음)
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
# proxmox_api_token    = "terraform@pve!terraform=<YOUR-TOKEN-UUID>"
# proxmox_ssh_password = "root 비밀번호"
# vm_ssh_public_key    = "ssh-ed25519 AAAA..."

# 2) 초기화
terraform init

# 3) 계획 확인
terraform plan

# 4) 적용
terraform apply

# 5) 삭제 (주의)
terraform destroy
```

## VM 101 (worker-gpu) 스펙

| 항목 | 값 |
|------|-----|
| VM ID | 101 |
| 호스트명 | worker-gpu |
| CPU | 8코어 |
| RAM | 16GB |
| Disk | 64GB (local-lvm) |
| GPU | RTX 3080 PCIe Passthrough |
| OS | Ubuntu 24.04 (cloud-init) |
| 네트워크 | vmbr0 (DHCP) |

## 주의사항
- `terraform.tfvars` 는 `.gitignore` 에 포함 (민감 정보 포함)
- GPU passthrough 이동 순서:
  1. `terraform apply` 로 VM 101 생성
  2. VM 100 정지 → `qm set 100 --delete hostpci0`
  3. VM 101 정지 → `qm set 101 --hostpci0 0000:06:00,pcie=1,x-vga=0`
  4. VM 101 시작
