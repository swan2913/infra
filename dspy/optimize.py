"""
DSPy 인프라 태스크 프롬프트 최적화 스크립트
실행: python3 dspy/optimize.py
결과: dspy/runs/<timestamp>_result.json + /opt/hermes/data/config.yaml 갱신
"""
import json
import os
import sys
import datetime
import random
import re
import yaml

import dspy
from dspy.teleprompt import BootstrapFewShot, MIPROv2

# ── 설정 ──────────────────────────────────────────────────────────────────────
API_BASE    = "http://192.168.1.24:30800/v1"
MODEL_NAME  = "Carnice-9b-Q6_K.gguf"
DATASET     = os.path.join(os.path.dirname(__file__), "dataset.json")
RUNS_DIR    = os.path.join(os.path.dirname(__file__), "runs")
HERMES_CFG  = "/opt/hermes/data/config.yaml"
TRAIN_RATIO = 0.8
SEED        = 42

# ── DSPy Signature ────────────────────────────────────────────────────────────
class InfraSignature(dspy.Signature):
    """
    You are an infrastructure agent on a Proxmox VE host (192.168.1.94).
    Given a user question about the homelab infrastructure, output the correct
    shell command to execute. Rules:
    - GPU/VRAM: use ssh -i /opt/data/vm_key ubuntu@192.168.1.24 nvidia-smi
    - llama.cpp logs/status: use kubectl logs -n vllm deployment/vllm
    - k8s state: use kubectl directly (kubectl is installed on this host)
    - VM management: use qm commands
    - Terraform: use cd /infra/terraform/proxmox && terraform ...
    - This host has NO GPU. Never run nvidia-smi directly.
    """
    question: str = dspy.InputField(desc="인프라 관련 사용자 질문")
    command: str  = dspy.OutputField(desc="실행할 쉘 명령어 (한 줄)")


class InfraAgent(dspy.Module):
    def __init__(self):
        self.predict = dspy.ChainOfThought(InfraSignature)

    def forward(self, question):
        return self.predict(question=question)


# ── 평가 메트릭 ───────────────────────────────────────────────────────────────
def metric(example, prediction, trace=None):
    cmd = prediction.command.lower() if hasattr(prediction, "command") else ""

    # must_contain 전부 포함
    for token in example.get("must_contain", []):
        if token.lower() not in cmd:
            return False

    # must_not_contain 전부 미포함
    for token in example.get("must_not_contain", []):
        if token.lower() in cmd:
            return False

    return True


def safe_call(agent, question):
    try:
        return agent(question=question)
    except Exception:
        class _Empty:
            command = ""
        return _Empty()


def score_dataset(agent, examples):
    correct = sum(1 for ex in examples if metric(ex, safe_call(agent, ex["question"])))
    return correct / len(examples) if examples else 0


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(RUNS_DIR, timestamp)
    os.makedirs(run_dir, exist_ok=True)

    # LM 설정
    lm = dspy.LM(
        f"openai/{MODEL_NAME}",
        api_base=API_BASE,
        api_key="none",
        max_tokens=6000,
        temperature=0.0,
    )
    dspy.configure(lm=lm)

    # 데이터셋 로드 및 분리
    with open(DATASET) as f:
        data = json.load(f)

    random.seed(SEED)
    random.shuffle(data)
    split = int(len(data) * TRAIN_RATIO)
    train_data = data[:split]
    eval_data  = data[split:]

    # dspy.Example 형식으로 변환
    def to_example(item):
        return dspy.Example(
            question=item["question"],
            command=item["expected_command"],
            must_contain=item.get("must_contain", []),
            must_not_contain=item.get("must_not_contain", []),
        ).with_inputs("question")

    train_examples = [to_example(d) for d in train_data]
    eval_examples  = [to_example(d) for d in eval_data]

    agent = InfraAgent()

    # 최적화 전 베이스라인
    print("=== 베이스라인 평가 ===")
    baseline = score_dataset(agent, eval_examples)
    print(f"Baseline 정확도: {baseline:.1%} ({int(baseline*len(eval_examples))}/{len(eval_examples)})")

    # BootstrapFewShot 최적화
    print("\n=== DSPy BootstrapFewShot 최적화 시작 ===")
    optimizer = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=4,
        max_labeled_demos=4,
    )
    optimized = optimizer.compile(agent, trainset=train_examples)

    # 최적화 후 평가
    print("\n=== 최적화 후 평가 ===")
    optimized_score = score_dataset(optimized, eval_examples)
    print(f"Optimized 정확도: {optimized_score:.1%} ({int(optimized_score*len(eval_examples))}/{len(eval_examples)})")
    print(f"개선: {(optimized_score - baseline):+.1%}")

    # few-shot 예시 추출 (ChainOfThought → predict.predict.demos)
    demos = []
    try:
        raw_demos = optimized.predict.predict.demos
        for demo in raw_demos:
            demos.append({
                "question": demo["question"],
                "command":  demo["command"],
            })
    except Exception:
        pass

    # 결과 저장
    result = {
        "timestamp":       timestamp,
        "baseline_score":  baseline,
        "optimized_score": optimized_score,
        "improvement":     optimized_score - baseline,
        "train_size":      len(train_examples),
        "eval_size":       len(eval_examples),
        "demos":           demos,
    }
    result_path = os.path.join(run_dir, "result.json")
    with open(result_path, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {result_path}")

    # Hermes config.yaml 갱신
    if os.path.exists(HERMES_CFG):
        with open(HERMES_CFG) as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    # few-shot 예시를 system_prompt 하단에 추가
    few_shot_block = ""
    if demos:
        few_shot_block = "\n\n## Verified Examples\n"
        for d in demos:
            few_shot_block += f"Q: {d['question']}\nA: {d['command']}\n\n"

    base_prompt = cfg.get("agent", {}).get("system_prompt", "")
    # 기존 Examples 블록 제거 후 새로 추가
    base_prompt = re.sub(r"\n\n## Verified Examples.*", "", base_prompt, flags=re.DOTALL)
    cfg.setdefault("agent", {})["system_prompt"] = base_prompt + few_shot_block

    with open(HERMES_CFG, "w") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

    print(f"Hermes config 갱신 완료: {HERMES_CFG}")
    print("\n다음 명령으로 Hermes에 반영:")
    print("  sudo systemctl restart hermes")

    return result


if __name__ == "__main__":
    main()
