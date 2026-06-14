"""
routes/telegram_webhook.py
מקבל עדכונים מ-Telegram Bot API ומעביר לאותו handler כמו heyy.

רישום webhook (חד-פעמי):
  GET /webhook/telegram/set  → רושם את ה-URL אצל טלגרם

Payload טיפוסי מטלגרם:
{
  "update_id": 123,
  "message": {
    "from": { "id": 223225844, "first_name": "רון" },
    "chat": { "id": 223225844 },
    "text": "תוסיף חלב"
  }
}
"""

import logging
import os

import requests
from flask import Blueprint, request, jsonify

from routes.webhook import _handle   # אותו handler מרכזי

log = logging.getLogger(__name__)
telegram_bp = Blueprint("telegram", __name__)


@telegram_bp.route("/", methods=["POST"])
def receive():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": True}), 200

    # תמיכה ב-message ו-callback_query (כפתורים)
    msg = data.get("message") or data.get("callback_query", {}).get("message")
    if not msg:
        return jsonify({"ok": True}), 200

    chat_id   = str(msg.get("chat", {}).get("id", ""))
    text      = (msg.get("text") or data.get("callback_query", {}).get("data") or "").strip()
    from_data = msg.get("from", {})
    name      = from_data.get("first_name", "") + " " + from_data.get("last_name", "")
    name      = name.strip()

    # סנן הודעות ריקות (תמונות, קבצים וכו')
    if not chat_id or not text:
        return jsonify({"ok": True}), 200

    # התעלם ממשתמשים שאינם רון (אבטחה בסיסית)
    allowed = os.getenv("TELEGRAM_CHAT_ID", "")
    if allowed and chat_id != allowed:
        log.warning("unauthorized telegram user: %s", chat_id)
        return jsonify({"ok": True}), 200

    log.info("telegram | chat_id=%s | text=%s", chat_id, text[:80])

    try:
        _handle(phone=chat_id, text=text, name=name)
    except Exception as exc:
        log.exception("telegram handler error: %s", exc)
        from services.telegram_service import send_message
        send_message(chat_id, "אוי, משהו השתבש. נסה שוב בעוד רגע")

    return jsonify({"ok": True}), 200


@telegram_bp.route("/set", methods=["GET"])
def set_webhook():
    """
    רשום את ה-webhook URL אצל טלגרם.
    קרא ל-endpoint הזה פעם אחת אחרי deploy:
      GET /webhook/telegram/set?url=https://your-domain.com
    """
    base_url = request.args.get("url", "").rstrip("/")
    if not base_url:
        return jsonify({"error": "url param required, e.g. ?url=https://your-domain.com"}), 400

    webhook_url = f"{base_url}/webhook/telegram/"
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    res = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={"url": webhook_url, "drop_pending_updates": True},
        timeout=10,
    )
    return jsonify(res.json()), res.status_code


@telegram_bp.route("/info", methods=["GET"])
def webhook_info():
    """בדוק את סטטוס ה-webhook הנוכחי."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    res = requests.get(
        f"https://api.telegram.org/bot{token}/getWebhookInfo",
        timeout=10,
    )
    return jsonify(res.json()), res.status_code
