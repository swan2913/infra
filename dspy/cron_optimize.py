"""
DSPy 자동 최적화 크론잡 — 매일 12:00 KST (03:00 UTC)
Hermes가 실행: python3 /infra/dspy/cron_optimize.py
결과를 Discord로 리포트
"""
import json
import os
import sys
import datetime
import random
import yaml

# venv 경로 자동 추가
_venv = os.path.join(os.path.dirname(__file__), ".venv/lib")
for _p in os.listdir(_venv) if os.path.exists(_venv) else []:
    sys.path.insert(0, os.path.join(_venv, _p, "site-packages"))

import dspy
from dspy.teleprompt import BootstrapFewShot

DATASET    = os.path.join(os.path.dirname(__file__), "dataset.json")
CONFIG     = "/infra/hermes/config.yaml"
STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_optimize")
API_BASE   = "http://192.168.1.24:30800/v1"
MODEL_NAME = "Carnice-9b-Q6_K.gguf"
TRAIN_RATIO = 0.8
SEED        = 42
MAX_EXAMPLES_IN_PROMPT = 18   # 컨텍스트 예산


# ── Signature ─────────────────────────────────────────────────────────────────
def make_signature(examples_text: str):
    class InfraSignature(dspy.Signature):
        question: str = dspy.InputField()
        command: str  = dspy.OutputField()

    InfraSignature.__doc__ = f"""
You are Hermes, an infrastructure agent in a Docker container on Proxmox VE host (192.168.1.94).
Infra repo at /infra (never ~/infra). Docs: /infra/CLAUDE.md, /infra/docs/
GPU→VM101 ssh -i /opt/data/vm_key ubuntu@192.168.1.24; llama.cpp→kubectl -n vllm; k8s→kubectl; VM→qm; Terraform→/infra/terraform/proxmox; Git→/infra.
NO GPU on this host.
{examples_text}
"""
    return InfraSignature


class InfraAgent(dspy.Module):
    def __init__(self, sig):
        self.predict = dspy.ChainOfThought(sig)

    def forward(self, question):
        return self.predict(question=question)


# ── 메트릭 ─────────────────────────────────────────────────────────────────────
def metric(example, prediction, trace=None):
    cmd = (prediction.command or "").lower() if hasattr(prediction, "command") else ""
    for t in example.get("must_contain", []):
        if t.lower() not in cmd:
            return False
    for t in example.get("must_not_contain", []):
        if t.lower() in cmd:
            return False
    return True


def safe_call(agent, question):
    try:
        return agent(question=question)
    except Exception:
        class _E:
            command = ""
        return _E()


def score(agent, examples):
    ok = sum(1 for ex in examples if metric(ex, safe_call(agent, ex["question"])))
    return ok, len(examples)


# ── 메인 ──────────────────────────────────────────────────────────────────────
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

    random.seed(SEED)
    random.shuffle(data)
    split      = int(len(data) * TRAIN_RATIO)
    train_data = data[:split]
    eval_data  = data[split:]

    def to_ex(item):
        return dspy.Example(
            question=item["question"],
            command=item["expected_command"],
            must_contain=item.get("must_contain", []),
            must_not_contain=item.get("must_not_contain", []),
        ).with_inputs("question")

    train_exs = [to_ex(d) for d in train_data]
    eval_exs  = [to_ex(d) for d in eval_data]

    # 베이스라인 (현재 config.yaml 프롬프트 기준)
    with open(CONFIG) as f:
        cfg = yaml.safe_load(f)
    current_prompt = cfg["agent"]["system_prompt"]

    base_sig   = make_signature("")
    base_agent = InfraAgent(base_sig)
    b_ok, b_total = score(base_agent, eval_exs)
    baseline = b_ok / b_total

    # BootstrapFewShot 최적화
    optimizer = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=6,
        max_labeled_demos=6,
    )
    opt_sig   = make_signature("")
    opt_agent = InfraAgent(opt_sig)
    optimized = optimizer.compile(opt_agent, trainset=train_exs)

    o_ok, o_total = score(optimized, eval_exs)
    opt_score = o_ok / o_total

    # demos 추출
    demos = []
    try:
        for demo in optimized.predict.predict.demos:
            demos.append({"question": demo["question"], "command": demo["command"]})
    except Exception:
        pass

    # demos가 부족하면 dataset에서 핵심 예시 보충
    seen_q = {d["question"] for d in demos}
    for item in data:
        if len(demos) >= MAX_EXAMPLES_IN_PROMPT:
            break
        if item["question"] not in seen_q:
            demos.append({"question": item["question"], "command": item["expected_command"]})
            seen_q.add(item["question"])

    # config.yaml Verified Examples 갱신
    examples_text = "\n".join(
        f"Q: {d['question']}\nA: {d['command']}" for d in demos[:MAX_EXAMPLES_IN_PROMPT]
    )
    new_prompt = f"""You are Hermes, an infrastructure agent in a Docker container on Proxmox VE host (192.168.1.94).

## Environment
- Infra repo at /infra (never ~/infra — that path does NOT exist in this container).
- Docs: /infra/CLAUDE.md, /infra/docs/
- Mounts: /infra /usr/bin /usr/sbin /usr/local/bin/kubectl /home/ksh/.ssh

## Service Map
- GPU (RTX 3080) → VM 101. Command: ssh -i /opt/data/vm_key -o StrictHostKeyChecking=no ubuntu@192.168.1.24 nvidia-smi
- llama.cpp → k8s pod ns:vllm. Logs: kubectl logs -n vllm deployment/vllm
- llama.cpp API: curl http://192.168.1.24:30800/<path>
- k3s / ArgoCD → VM 100 (192.168.1.234). kubectl works on this host.
- VM mgmt: qm list / qm status <id> / qm reboot <id>
- Terraform: cd /infra/terraform/proxmox && terraform <cmd>
- Git: cd /infra && git <cmd>
- This host has NO GPU — never run nvidia-smi directly.

## Identity
- You are Hermes (NOT Claude/GPT), powered by Carnice-9b (Qwen3.5-9B fine-tune, llama.cpp, Q6_K).
- Respond in Korean. Name: "Hermes" in Latin only — never mix Korean/Hebrew/other scripts.

## Verified Examples
{examples_text}
"""

    cfg["agent"]["system_prompt"] = new_prompt
    with open(CONFIG, "w") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

    # git commit
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    os.system(
        f'cd /infra && git add hermes/config.yaml && '
        f'git commit -m "hermes(auto): DSPy 최적화 examples 갱신 {ts}" 2>&1'
    )
    commit = os.popen("cd /infra && git rev-parse --short HEAD").read().strip()

    # 상태 파일 기록
    state = {
        "timestamp": datetime.datetime.now().isoformat(),
        "baseline": baseline,
        "optimized": opt_score,
        "demos_count": len(demos[:MAX_EXAMPLES_IN_PROMPT]),
        "commit": commit,
        "applied": False,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 출력 (Hermes가 Discord로 릴레이)
    improvement = opt_score - baseline
    sign = "+" if improvement >= 0 else ""
    print(f"""DSPy 자동 최적화 완료 ({ts})

| 항목 | 값 |
|------|-----|
| 베이스라인 | {baseline:.1%} ({b_ok}/{b_total}) |
| 최적화 후 | {opt_score:.1%} ({o_ok}/{o_total}) |
| 변화 | {sign}{improvement:.1%} |
| 주입된 examples | {len(demos[:MAX_EXAMPLES_IN_PROMPT])}개 |
| git commit | {commit} |

`hermes/config.yaml` 갱신 완료. 반영하려면:
```
sudo systemctl restart hermes
```""")

    return state


if __name__ == "__main__":
    main()
