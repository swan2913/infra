"""
Hermes 인프라 태스크 성능 평가 스크립트
실행: python3 dspy/evaluate.py
system prompt는 hermes/config.yaml에서 읽어 항상 현재 상태를 반영
"""
import json
import os
import datetime

import yaml
import dspy

API_BASE   = "http://192.168.1.24:30800/v1"
MODEL_NAME = "Carnice-9b-Q6_K.gguf"
DATASET    = os.path.join(os.path.dirname(__file__), "dataset.json")
CONFIG     = os.path.join(os.path.dirname(__file__), "../hermes/config.yaml")
RUNS_DIR   = os.path.join(os.path.dirname(__file__), "runs")


def load_signature():
    """hermes/config.yaml의 system_prompt를 InfraSignature docstring으로 사용."""
    cfg_path = os.path.abspath(CONFIG)
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    prompt = cfg["agent"]["system_prompt"]

    class InfraSignature(dspy.Signature):
        question: str = dspy.InputField()
        command: str  = dspy.OutputField()

    InfraSignature.__doc__ = prompt
    return InfraSignature


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
    try:
        return agent(question=question)
    except Exception:
        return FailedPrediction()


def main():
    lm = dspy.LM(
        f"openai/{MODEL_NAME}",
        api_base=API_BASE,
        api_key="none",
        max_tokens=12000,  # Qwen3.5 thinking 토큰 포함 여유있게
        temperature=0.0,
    )
    dspy.configure(lm=lm)

    with open(DATASET) as f:
        data = json.load(f)

    InfraSignature = load_signature()
    agent = dspy.Predict(InfraSignature)

    results = []
    passed = 0
    errors = 0
    print(f"{'질문':<40} {'결과':<6} {'출력 명령어'}")
    print("-" * 100)

    for item in data:
        pred   = safe_predict(agent, item["question"])
        ok     = metric(item, pred)
        failed = pred.command == "" and not ok
        if ok:
            passed += 1
        if failed:
            errors += 1
        results.append({
            "question":         item["question"],
            "expected":         item["expected_command"],
            "predicted":        pred.command,
            "passed":           ok,
            "parse_error":      failed,
            "must_contain":     item.get("must_contain", []),
            "must_not_contain": item.get("must_not_contain", []),
        })
        status = "✅" if ok else ("💥" if failed else "❌")
        print(f"{item['question'][:38]:<40} {status:<6} {pred.command[:50]}")

    score = passed / len(data)
    print(f"\n총 정확도: {score:.1%} ({passed}/{len(data)})  파싱실패: {errors}개")

    os.makedirs(RUNS_DIR, exist_ok=True)
    ts   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(RUNS_DIR, f"{ts}_eval.json")
    with open(path, "w") as f:
        json.dump({"timestamp": ts, "score": score, "results": results}, f,
                  ensure_ascii=False, indent=2)
    print(f"결과 저장: {path}")


if __name__ == "__main__":
    main()
