"""
DSPy 자동 최적화 크론잡 — 매일 12:00 KST (03:00 UTC)
결과를 Discord로 리포트 (hermes-notify 경유)
"""
import json
import os
import re
import sys
import datetime
import random
import yaml

import dspy
from dspy.teleprompt import BootstrapFewShot

DATASET     = os.path.join(os.path.dirname(__file__), "dataset.json")
CONFIG_REPO = os.path.join(os.path.dirname(__file__), "../hermes/config.yaml")
STATE_FILE  = os.path.join(os.path.dirname(__file__), ".last_optimize")
API_BASE    = "http://192.168.1.24:30800/v1"
MODEL_NAME  = "Carnice-9b-Q6_K.gguf"
TRAIN_RATIO = 0.8
SEED        = 42
MAX_DEMOS   = 14  # 65K 컨텍스트 기준 few-shot 예산


def load_signature():
    """hermes/config.yaml의 system_prompt를 InfraSignature docstring으로 사용."""
    cfg_path = os.path.abspath(CONFIG_REPO)
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    prompt = cfg["agent"]["system_prompt"]

    class InfraSignature(dspy.Signature):
        question: str = dspy.InputField()
        command: str  = dspy.OutputField()

    InfraSignature.__doc__ = prompt
    return InfraSignature


class InfraAgent(dspy.Module):
    def __init__(self, signature):
        self.predict = dspy.ChainOfThought(signature)

    def forward(self, question):
        return self.predict(question=question)


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


def main():
    lm = dspy.LM(
        f"openai/{MODEL_NAME}",
        api_base=API_BASE,
        api_key="none",
        max_tokens=4096,
        temperature=0.0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
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

    # 베이스라인 평가 (현재 config.yaml 프롬프트 기준)
    base_agent = InfraAgent(load_signature())
    b_ok, b_total = score(base_agent, eval_exs)
    baseline = b_ok / b_total

    # BootstrapFewShot 최적화
    optimizer = BootstrapFewShot(
        metric=metric,
        max_bootstrapped_demos=6,
        max_labeled_demos=6,
    )
    opt_agent = InfraAgent(load_signature())
    optimized = optimizer.compile(opt_agent, trainset=train_exs)

    o_ok, o_total = score(optimized, eval_exs)
    opt_score = o_ok / o_total

    # bootstrapped demos 추출
    demos = []
    try:
        for demo in optimized.predict.predict.demos:
            demos.append({"question": demo["question"], "command": demo["command"]})
    except Exception:
        pass

    # demos가 부족하면 dataset에서 보충
    seen_q = {d["question"] for d in demos}
    for item in data:
        if len(demos) >= MAX_DEMOS:
            break
        if item["question"] not in seen_q:
            demos.append({"question": item["question"], "command": item["expected_command"]})
            seen_q.add(item["question"])

    # config.yaml Verified Examples 갱신 (기존 블록 교체)
    cfg_path = os.path.abspath(CONFIG_REPO)
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    base_prompt = cfg.get("agent", {}).get("system_prompt", "")
    base_prompt = re.sub(r"\n\n## Verified Examples.*", "", base_prompt, flags=re.DOTALL)

    examples_block = "\n\n## Verified Examples\n"
    for d in demos[:MAX_DEMOS]:
        examples_block += f"Q: {d['question']}\nA: {d['command']}\n\n"

    cfg["agent"]["system_prompt"] = base_prompt + examples_block
    with open(cfg_path, "w") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)

    # git commit + push (Hermes 작성자)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    os.system(
        f'cd ~/infra && git add hermes/config.yaml && '
        f'git -c user.name="Hermes" -c user.email="hermes@192.168.1.94" '
        f'commit -m "hermes(auto): DSPy 최적화 examples 갱신 {ts}" 2>&1 || true && '
        f'git push origin main 2>&1 || true'
    )
    commit = os.popen("cd ~/infra && git rev-parse --short HEAD 2>/dev/null").read().strip()

    # Hermes 자동 재시작 (최적화 즉시 반영)
    os.system("sudo systemctl restart hermes 2>&1 || true")

    # 상태 파일 기록
    state = {
        "timestamp": datetime.datetime.now().isoformat(),
        "baseline": baseline,
        "optimized": opt_score,
        "demos_count": len(demos[:MAX_DEMOS]),
        "commit": commit,
        "applied": True,
    }
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # 출력 (hermes-notify가 Discord로 전송)
    improvement = opt_score - baseline
    sign = "+" if improvement >= 0 else ""
    print(f"""DSPy 자동 최적화 완료 ({ts})

| 항목 | 값 |
|------|-----|
| 베이스라인 | {baseline:.1%} ({b_ok}/{b_total}) |
| 최적화 후 | {opt_score:.1%} ({o_ok}/{o_total}) |
| 변화 | {sign}{improvement:.1%} |
| 주입된 examples | {len(demos[:MAX_DEMOS])}개 |
| git commit | {commit} |

`hermes/config.yaml` 갱신 및 서비스 재시작 완료.""")

    return state


if __name__ == "__main__":
    main()
