#!/usr/bin/env python3
"""One-time: create + pin the tracker data message in the Telegram chat."""

import json
import os
import urllib.request

from dotenv import load_dotenv

load_dotenv()
TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT = os.environ["TELEGRAM_CHAT_ID"]


def tg(method, params):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/{method}",
        data=json.dumps(params).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if not out.get("ok"):
        raise RuntimeError(f"{method}: {out}")
    return out["result"]


chat = tg("getChat", {"chat_id": CHAT})
pm = chat.get("pinned_message") or {}
if "JTRACK::" in (pm.get("text") or ""):
    print(f"Data message already pinned (id {pm['message_id']}).")
else:
    payload = "Internship tracker data \u2014 do not unpin or delete\nJTRACK::" + json.dumps(
        {"applied": {}, "notified": {}, "deadlines": [], "updatedAt": 0}
    )
    msg = tg("sendMessage", {"chat_id": CHAT, "text": payload, "disable_notification": True})
    tg("pinChatMessage", {"chat_id": CHAT, "message_id": msg["message_id"], "disable_notification": True})
    print(f"Pinned new data message (id {msg['message_id']}).")
