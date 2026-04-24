#!/usr/bin/env bash
set -euo pipefail

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

helm repo add run-ai https://run-ai.github.io/helm-charts
helm repo update

helm upgrade --install kai-scheduler run-ai/kai-scheduler \
  --namespace kai-scheduler \
  --create-namespace \
  --wait
