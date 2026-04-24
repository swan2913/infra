#!/usr/bin/env bash
set -euo pipefail

# Helm 설치 확인
if ! command -v helm &>/dev/null; then
  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
fi

# kubeconfig
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

helm repo add nvidia https://helm.ngc.nvidia.com/nvidia
helm repo update

helm upgrade --install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace \
  --values values.yaml \
  --wait
