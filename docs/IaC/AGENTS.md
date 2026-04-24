# IaC 도메인 에이전트 규칙

## 담당 범위
Terraform (Proxmox VM 프로비저닝), Ansible (VM 내부 설정).

## 작업 원칙

- `terraform.tfvars` 는 절대 git commit 금지 (API 토큰, 비밀번호 포함)
- `terraform plan` 먼저 확인 후 `terraform apply`
- Terraform이 관리하는 VM은 PVE 웹 UI나 `qm` 으로 직접 수정 금지
- Ansible 실행 전 `ansible ... -m ping` 으로 접속 확인

## Terraform 작업 순서

```bash
cd ~/infra/terraform/proxmox
terraform init        # provider 다운로드 (최초 1회)
terraform plan        # 변경 사항 미리 확인
terraform apply       # 실제 적용
terraform show        # 현재 state 확인
```

## Ansible 작업 순서

```bash
cd ~/infra
# 접속 확인
ansible all -i ansible/inventory/hosts.ini -m ping

# playbook 실행
ansible-playbook -i ansible/inventory/hosts.ini \
  ansible/playbooks/<playbook>.yml \
  --check   # dry-run 먼저
ansible-playbook -i ansible/inventory/hosts.ini \
  ansible/playbooks/<playbook>.yml
```

## 파일 위치
- Terraform: `terraform/proxmox/`
- Ansible inventory: `ansible/inventory/hosts.ini`
- Ansible playbooks: `ansible/playbooks/`
- Terraform 문서: `docs/IaC/IaC-001-terraform-proxmox.md`
- Ansible 문서: `docs/IaC/IaC-002-ansible-playbooks.md`
