# K8S-001 · k3s 설치 및 기본 설정

> 환경: Ubuntu 24.04.4 / VM 100 (192.168.1.234)  
> 완료일: 2026-04-25

## k3s 선택 이유
- 단일 바이너리, 경량 (~70MB)
- 홈랩/엣지 환경에 적합
- Containerd 내장, GPU Operator 호환

## Step 1 · k3s Control Plane 설치

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC='server --disable traefik' sh -
# traefik 제외: Ingress는 추후 별도 구성

# 설치 확인
sudo k3s kubectl get nodes
# → ubuntu-1  Ready  control-plane  v1.34.6+k3s1
```

## Step 2 · kubeconfig 권한 설정

```bash
# k3s 설정 파일 생성
sudo tee /etc/rancher/k3s/config.yaml << 'EOF'
write-kubeconfig-mode: "0644"
EOF

sudo systemctl restart k3s && sleep 10

# 사용자 홈에 복사
mkdir -p ~/.kube
cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
chmod 600 ~/.kube/config

# 확인
kubectl get nodes -o wide
```

## Step 3 · Helm 설치

```bash
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version --short
# → v3.20.2
```

## k3s Worker 노드 조인 (VM 101, 추후)

```bash
# Control Plane에서 token 확인
cat /var/lib/rancher/k3s/server/node-token

# Worker 노드에서 실행
curl -sfL https://get.k3s.io | \
  K3S_URL="https://192.168.1.234:6443" \
  K3S_TOKEN="<token>" \
  sh -

# Control Plane에서 확인
kubectl get nodes
# → ubuntu-1   Ready  control-plane
# → worker-gpu Ready  <none>
```

## 현재 상태

```bash
kubectl get nodes -o wide
# NAME       STATUS   ROLES           AGE   VERSION        INTERNAL-IP
# ubuntu-1   Ready    control-plane   -     v1.34.6+k3s1   192.168.1.234

kubectl get pods -A
# NAMESPACE     NAME                        READY   STATUS
# kube-system   coredns-*                   1/1     Running
# kube-system   local-path-provisioner-*    1/1     Running
# kube-system   metrics-server-*            1/1     Running
```

## 유용한 명령어

```bash
# 노드 GPU 리소스 확인 (GPU Operator 설치 후)
kubectl describe node ubuntu-1 | grep -A5 "nvidia.com"

# k3s 서비스 관리
sudo systemctl status k3s
sudo systemctl restart k3s
sudo journalctl -u k3s -f
```
