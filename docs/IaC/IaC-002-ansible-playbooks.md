# IaC-002 · Ansible Playbook 구성

> Ansible로 VM 내부 설정 자동화  
> 완료일: 2026-04-25

## 인벤토리 구조

```ini
# ansible/inventory/hosts.ini
[control_plane]
ubuntu-1 ansible_host=192.168.1.234 ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/vm100_key

[workers]
# worker-gpu ansible_host=192.168.1.xxx ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/vm100_key

[k8s_cluster:children]
control_plane
workers

[pve_host]
pve ansible_host=192.168.1.94 ansible_user=ksh ansible_connection=local
```

## Playbook 목록

| 파일 | 대상 | 내용 |
|------|------|------|
| `setup-nvidia.yml` | workers | NVIDIA 드라이버 + Container Toolkit |
| `setup-k3s.yml` | control_plane | k3s Control Plane 설치 |
| `setup-k3s-agent.yml` | workers | k3s Worker Agent 조인 |

## 설치

```bash
sudo apt-get install -y ansible
ansible --version
```

## 실행 예시

```bash
cd ~/infra

# 핑 테스트
ansible all -i ansible/inventory/hosts.ini -m ping

# Control Plane k3s 설치
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-k3s.yml

# Worker NVIDIA 드라이버 설치
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-nvidia.yml

# Worker k3s agent 조인
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-k3s-agent.yml
```

## 워커 노드 추가 절차 (전체)

```bash
# 1. Terraform으로 VM 생성
cd terraform/proxmox && terraform apply

# 2. 생성된 VM IP를 hosts.ini에 추가
vim ansible/inventory/hosts.ini
# [workers] 섹션에 IP 추가

# 3. NVIDIA 드라이버 설치 (VM 재부팅 포함)
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-nvidia.yml

# 4. k3s agent 조인
ansible-playbook -i ansible/inventory/hosts.ini ansible/playbooks/setup-k3s-agent.yml

# 5. 노드 확인
ssh vm100 kubectl get nodes
```
