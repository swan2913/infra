#!/usr/bin/env python3
"""Discord DM 직접 전송 — hermes 컨테이너 내부에서 실행, LLM 없이 Discord Bot API 직접 호출
Usage: docker exec --user 10000:10000 hermes python3 /infra/scripts/discord-dm.py "message"
"""
import sys
import json
import os
import urllib.request
import urllib.error

USER_ID = "1372389480618659880"  # goseunghwan_54963


def send_dm(msg: str):
    token = os.environ.get("DISCORD_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN not set in container environment")

    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json",
        "User-Agent": "DiscordBot (hermes-agent, 1.0)",
    }

    req = urllib.request.Request(
        "https://discord.com/api/v10/users/@me/channels",
        data=json.dumps({"recipient_id": USER_ID}).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        channel_id = json.loads(r.read())["id"]

    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{channel_id}/messages",
        data=json.dumps({"content": msg}).encode(),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        r.read()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: discord-dm.py <message>", file=sys.stderr)
        sys.exit(1)
    send_dm(sys.argv[1])
    print("→ Discord DM 전송 완료")
