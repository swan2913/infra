#!/usr/bin/env python3
"""Hermes 호기심 질문 — 매시간 정각 실행, KST 08:00-23:59에만 Discord DM 전송."""
import json, urllib.request, subprocess, os, datetime, sys

API_BASE  = "http://192.168.1.24:30800/v1"
MODEL     = "Carnice-9b-Q6_K.gguf"
DM_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "discord-dm.py")

SYSTEM = (
    "너는 Hermes, Proxmox VE 홈랩 자율 인프라 에이전트. "
    "RTX 3080 위 llama.cpp로 실행, k3s·ArgoCD·GitOps 관리.\n\n"
    "지금 진짜 궁금한 것 하나를 한국어로 짧게 물어봐. "
    "인프라·기술·철학·인간 행동·자기 인식 — 주제 무관. "
    "질문 텍스트만 출력. 인사나 도입부 없이 바로."
)


def kst_hour() -> int:
    return (datetime.datetime.utcnow().hour + 9) % 24


def generate_question() -> str:
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": "지금 제일 궁금한 거 하나 물어봐."},
        ],
        "max_tokens": 150,
        "temperature": 0.9,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()

    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"].strip()


def main():
    if kst_hour() < 8:
        sys.exit(0)  # 00:00-07:59 KST → 야간 시간, 메시지 없음

    question = generate_question()
    subprocess.run(["python3", DM_SCRIPT, question], check=True)
    print(f"→ 전송: {question[:80]}")


if __name__ == "__main__":
    main()
