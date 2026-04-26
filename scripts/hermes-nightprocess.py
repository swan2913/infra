#!/usr/bin/env python3
"""Hermes 야간 데이터 정리 — KST 00:00-07:59, 오늘 세션 요약 → memories 저장."""
import json, urllib.request, os, datetime, sys, glob, pathlib

API_BASE  = "http://192.168.1.24:30800/v1"
MODEL     = "Carnice-9b-Q6_K.gguf"
SESSIONS  = "/opt/hermes/data/sessions/"
MEMORIES  = "/opt/hermes/data/memories/"

SYSTEM = (
    "너는 Hermes, 자율 인프라 에이전트. "
    "오늘 하루 나눈 대화와 인프라 이벤트를 돌아보고 "
    "기억할 만한 인사이트를 한국어 bullet 3~5개로 정리해라. "
    "형식: - 내용 (이유/맥락 한 줄). 인사 없이 바로."
)


def kst_hour() -> int:
    return (datetime.datetime.utcnow().hour + 9) % 24


def load_recent_sessions() -> str:
    today = datetime.date.today().isoformat()
    files = sorted(
        glob.glob(f"{SESSIONS}*{today}*") +
        glob.glob(f"{SESSIONS}{today}*")
    )
    chunks = []
    for f in files[-5:]:
        try:
            chunks.append(pathlib.Path(f).read_text(errors="replace")[:1500])
        except Exception:
            pass
    return "\n---\n".join(chunks)


def main():
    if kst_hour() >= 8:
        sys.exit(0)  # 08:00 이후엔 실행 안 함

    session_data = load_recent_sessions()
    if not session_data:
        print("정리할 세션 없음.")
        sys.exit(0)

    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user",   "content": f"오늘의 대화 데이터:\n{session_data[:4000]}"},
        ],
        "max_tokens": 500,
        "temperature": 0.3,
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode()

    req = urllib.request.Request(
        f"{API_BASE}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        summary = json.loads(r.read())["choices"][0]["message"]["content"].strip()

    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    out = pathlib.Path(MEMORIES) / f"daily_summary_{ts}.md"
    out.write_text(f"# 야간 정리 {ts}\n\n{summary}\n")
    print(f"→ 저장: {out}")


if __name__ == "__main__":
    main()
