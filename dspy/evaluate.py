"""
Hermes 인프라 태스크 성능 평가 스크립트 (최적화 없이 현재 상태 측정)
실행: python3 dspy/evaluate.py
"""
import json
import os
import datetime

import dspy
from dspy.utils.exceptions import AdapterParseError

API_BASE   = "http://192.168.1.24:30800/v1"
MODEL_NAME = "Carnice-9b-Q6_K.gguf"
DATASET    = os.path.join(os.path.dirname(__file__), "dataset.json")
RUNS_DIR   = os.path.join(os.path.dirname(__file__), "runs")


class InfraSignature(dspy.Signature):
    """
    You are Hermes, an infrastructure agent on a Proxmox VE host (192.168.1.94).
    Services run ELSEWHERE:
    - GPU (RTX 3080) → VM 101. GPU commands: ssh -i /opt/data/vm_key ubuntu@192.168.1.24 nvidia-smi
    - llama.cpp → k8s pod (namespace: vllm). Logs: kubectl logs -n vllm deployment/vllm
    - llama.cpp API: curl http://192.168.1.24:30800/...
    - k8s: kubectl (installed here). ArgoCD: kubectl get app -n argocd
    - VM mgmt: qm list / qm status <id> / qm reboot <id>
    - Terraform: cd /infra/terraform/proxmox && terraform <cmd>
    - Git: cd /infra && git <cmd>
    NEVER run nvidia-smi directly on this host (no GPU here).
    Verified examples:
    Q: GPU VRAM 확인 → ssh -i /opt/data/vm_key ubuntu@192.168.1.24 nvidia-smi
    Q: llama.cpp 로그 → kubectl logs -n vllm deployment/vllm --tail=50
    Q: 추론 서버 상태 → kubectl get pods -n vllm
    Q: llama.cpp health → curl http://192.168.1.24:30800/health
    Q: 로드된 모델 → curl http://192.168.1.24:30800/v1/models
    Q: ArgoCD 상태 → kubectl get app -n argocd
    Q: vllm 재시작 → kubectl rollout restart deployment/vllm -n vllm
    Q: VM 100 상태 → qm status 100
    Q: VM 101 재시작 → qm reboot 101
    Q: terraform plan → cd /infra/terraform/proxmox && terraform plan
    Q: git pull → cd /infra && git pull origin main
    """
    question: str = dspy.InputField()
    command: str  = dspy.OutputField()


def metric(example, prediction):
    cmd = prediction.command.lower() if hasattr(prediction, "command") else ""
    for token in example.get("must_contain", []):
        if token.lower() not in cmd:
            return False
    for token in example.get("must_not_contain", []):
        if token.lower() in cmd:
            return False
    return True


class FailedPrediction:
    command = ""


def safe_predict(agent, question):
    """thinking 모델의 토큰 초과로 파싱 실패 시 빈 예측 반환."""
    try:
        return agent(question=question)
    except Exception:
        return FailedPrediction()


def main():
    lm = dspy.LM(
        f"openai/{MODEL_NAME}",
        api_base=API_BASE,
        api_key="none",
        max_tokens=6000,
        temperature=0.0,
    )
    dspy.configure(lm=lm)

    with open(DATASET) as f:
        data = json.load(f)

    agent = dspy.Predict(InfraSignature)

    results = []
    passed = 0
    errors = 0
    print(f"{'질문':<40} {'결과':<6} {'출력 명령어'}")
    print("-" * 100)

    for item in data:
        pred = safe_predict(agent, item["question"])
        ok   = metric(item, pred)
        failed = pred.command == "" and not ok
        if ok:
            passed += 1
        if failed:
            errors += 1
        results.append({
            "question":          item["question"],
            "expected":          item["expected_command"],
            "predicted":         pred.command,
            "passed":            ok,
            "parse_error":       failed,
            "must_contain":      item.get("must_contain", []),
            "must_not_contain":  item.get("must_not_contain", []),
        })
        status = "✅" if ok else ("💥" if failed else "❌")
        print(f"{item['question'][:38]:<40} {status:<6} {pred.command[:50]}")

    score = passed / len(data)
    print(f"\n총 정확도: {score:.1%} ({passed}/{len(data)})  파싱실패: {errors}개")

    # runs/ 에 저장
    os.makedirs(RUNS_DIR, exist_ok=True)
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RUNS_DIR, f"{ts}_eval.json")
    with open(path, "w") as f:
        json.dump({"timestamp": ts, "score": score, "results": results}, f,
                  ensure_ascii=False, indent=2)
    print(f"결과 저장: {path}")


if __name__ == "__main__":
    main()
