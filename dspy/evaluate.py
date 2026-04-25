"""
Hermes 인프라 태스크 성능 평가 스크립트 (최적화 없이 현재 상태 측정)
실행: python3 dspy/evaluate.py
"""
import json
import os
import datetime

import dspy

API_BASE   = "http://192.168.1.24:30800/v1"
MODEL_NAME = "Carnice-9b-Q6_K.gguf"
DATASET    = os.path.join(os.path.dirname(__file__), "dataset.json")
RUNS_DIR   = os.path.join(os.path.dirname(__file__), "runs")


class InfraSignature(dspy.Signature):
    """Infrastructure agent: given a question, output the correct shell command."""
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


def main():
    lm = dspy.LM(
        f"openai/{MODEL_NAME}",
        api_base=API_BASE,
        api_key="none",
        max_tokens=200,
        temperature=0.0,
    )
    dspy.configure(lm=lm)

    with open(DATASET) as f:
        data = json.load(f)

    agent = dspy.Predict(InfraSignature)

    results = []
    passed = 0
    print(f"{'질문':<40} {'결과':<6} {'출력 명령어'}")
    print("-" * 100)

    for item in data:
        pred = agent(question=item["question"])
        ok   = metric(item, pred)
        if ok:
            passed += 1
        results.append({
            "question":          item["question"],
            "expected":          item["expected_command"],
            "predicted":         pred.command,
            "passed":            ok,
            "must_contain":      item.get("must_contain", []),
            "must_not_contain":  item.get("must_not_contain", []),
        })
        status = "✅" if ok else "❌"
        print(f"{item['question'][:38]:<40} {status:<6} {pred.command[:50]}")

    score = passed / len(data)
    print(f"\n총 정확도: {score:.1%} ({passed}/{len(data)})")

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
