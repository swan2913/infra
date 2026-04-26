"""
DSPy 리마인더 크론잡 — 매일 18:00 KST (09:00 UTC)
오늘 최적화가 실행됐지만 아직 Hermes가 재시작되지 않았으면 알림 전송
"""
import json
import os
import datetime

STATE_FILE = os.path.join(os.path.dirname(__file__), ".last_optimize")


def main():
    if not os.path.exists(STATE_FILE):
        return  # 오늘 최적화 없음, 조용히 종료

    with open(STATE_FILE) as f:
        state = json.load(f)

    opt_time = datetime.datetime.fromisoformat(state["timestamp"])
    today    = datetime.datetime.now().date()

    # 오늘 실행된 최적화가 아니면 조용히 종료
    if opt_time.date() != today:
        return

    # 이미 적용 완료 표시가 있으면 종료
    if state.get("applied"):
        return

    commit = state.get("commit", "?")
    b  = state.get("baseline", 0)
    o  = state.get("optimized", 0)
    sign = "+" if o - b >= 0 else ""

    print(f"""⏰ DSPy 최적화 미적용 리마인더

오늘 {opt_time.strftime('%H:%M')} 에 최적화가 완료됐지만 아직 반영되지 않았어요.

변화: {b:.1%} → {o:.1%} ({sign}{o-b:.1%})
commit: {commit}

반영하려면:
```
sudo systemctl restart hermes
```""")


if __name__ == "__main__":
    main()
