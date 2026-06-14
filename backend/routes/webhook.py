"""
routes/webhook.py
מקבל הודעות מ-Telegram, מזהה משתמש, מבין כוונה ומחזיר תשובה.

Endpoints:
  POST /webhook/          ← Telegram שולח לכאן כל הודעה
  GET  /webhook/set?url=  ← רשום webhook אצל Telegram (פעם אחת)
  GET  /webhook/info      ← בדוק סטטוס webhook
"""

import logging
import os
import requests
from flask import Blueprint, request, jsonify

from services.claude_service import understand_message
from services.telegram_service import (
    send_message,
    send_shopping_list,
    send_bills_summary,
    send_tasks_summary,
    send_confirmation,
)
from services.supabase_service import (
    get_or_create_household_by_phone,
    get_user_by_phone,
    get_household_members,
    get_shopping_list,
    add_shopping_item,
    find_item_by_name,
    update_shopping_item,
    delete_shopping_item,
    clear_bought_items,
    get_bills,
    add_bill,
    mark_bill_paid,
    get_tasks,
    add_task,
    update_task_status,
)

log = logging.getLogger(__name__)
webhook_bp = Blueprint("webhook", __name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def _tg(method: str, **kwargs) -> dict:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    res = requests.post(
        TELEGRAM_API.format(token=token, method=method),
        json=kwargs, timeout=10,
    )
    return res.json()


# ══════════════════════════════════════════════════════════════
# Webhook management
# ══════════════════════════════════════════════════════════════

@webhook_bp.route("/set", methods=["GET"])
def set_webhook():
    """רשום webhook אצל Telegram. קרא פעם אחת אחרי שה-ngrok URL מוכן."""
    base = request.args.get("url", "").rstrip("/")
    if not base:
        return jsonify({"error": "חסר ?url=https://your-ngrok-url"}), 400

    webhook_url = f"{base}/webhook/"
    res = _tg("setWebhook", url=webhook_url, drop_pending_updates=True)
    return jsonify(res)


@webhook_bp.route("/info", methods=["GET"])
def webhook_info():
    """בדוק איזה webhook רשום כרגע."""
    return jsonify(_tg("getWebhookInfo"))


# ══════════════════════════════════════════════════════════════
# קבלת הודעות מ-Telegram
# ══════════════════════════════════════════════════════════════

@webhook_bp.route("/", methods=["POST"])
def receive():
    """
    Telegram שולח POST לכאן על כל הודעה.
    Payload:
    {
      "update_id": 123,
      "message": {
        "from": { "id": 223225844, "first_name": "רון" },
        "chat": { "id": 223225844 },
        "text": "תוסיף חלב"
      }
    }
    """
    data = request.get_json(silent=True) or {}

    # תמיכה ב-message ו-callback_query (לחיצה על כפתור)
    msg = data.get("message") or data.get("callback_query", {}).get("message")
    if not msg:
        return jsonify({"ok": True}), 200

    chat_id = str(msg.get("chat", {}).get("id", ""))
    text    = (msg.get("text") or data.get("callback_query", {}).get("data") or "").strip()
    sender  = msg.get("from", {})
    name    = f"{sender.get('first_name','')} {sender.get('last_name','')}".strip()

    if not chat_id or not text:
        return jsonify({"ok": True}), 200

    # אבטחה: קבל רק מ-chat_id המורשה
    allowed = os.getenv("TELEGRAM_CHAT_ID", "")
    if allowed and chat_id != allowed:
        log.warning("unauthorized: %s", chat_id)
        return jsonify({"ok": True}), 200

    log.info("telegram | %s | %s", chat_id, text[:80])

    try:
        _handle(phone=chat_id, text=text, name=name)
    except Exception as exc:
        log.exception("handler error: %s", exc)
        send_message(chat_id, "אוי, משהו השתבש 😅 נסה שוב")

    return jsonify({"ok": True}), 200


# ══════════════════════════════════════════════════════════════
# ניתוב מרכזי — זהה לחלוטין ללא קשר לערוץ
# ══════════════════════════════════════════════════════════════

def _handle(phone: str, text: str, name: str) -> None:
    household = get_or_create_household_by_phone(phone, name=name)
    hid       = household["id"]
    user      = get_user_by_phone(phone)
    uid       = user["id"] if user else None
    members   = get_household_members(hid)

    result = understand_message(
        text,
        sender_name=name or (user["name"] if user else ""),
        household_context={"members": members},
    )

    intent = result.get("intent", "general")
    params = result.get("params", {})
    reply  = result.get("reply", "אוקיי!")

    log.info("intent=%s params=%s", intent, params)

    handlers = {
        "add_shopping":    _add_shopping,
        "remove_shopping": _remove_shopping,
        "bought_shopping": _bought_shopping,
        "list_shopping":   _list_shopping,
        "clear_bought":    _clear_bought,
        "add_bill":        _add_bill,
        "mark_bill_paid":  _mark_bill_paid,
        "list_bills":      _list_bills,
        "add_task":        _add_task,
        "list_tasks":      _list_tasks,
        "done_task":       _done_task,
    }

    handler = handlers.get(intent)
    if handler:
        handler(phone, hid, uid, params, reply, members)
    else:
        send_message(phone, reply)


# ══════════════════════════════════════════════════════════════
# Handlers — קניות
# ══════════════════════════════════════════════════════════════

def _add_shopping(phone, hid, uid, params, reply, members):
    name = params.get("name", "").strip()
    if not name:
        send_message(phone, "לא הבנתי מה להוסיף, נסה שוב")
        return
    if find_item_by_name(hid, name):
        send_message(phone, f"*{name}* כבר ברשימה")
        return
    add_shopping_item(
        household_id=hid, name=name,
        quantity=params.get("quantity", ""),
        category=params.get("category", "כללי"),
        added_by=uid, priority=params.get("priority", 0),
    )
    send_confirmation(phone, "added_shopping", name)


def _remove_shopping(phone, hid, uid, params, reply, members):
    name = params.get("name", "").strip()
    item = find_item_by_name(hid, name)
    if not item:
        send_message(phone, f"לא מצאתי *{name}* ברשימה")
        return
    delete_shopping_item(item["id"])
    send_confirmation(phone, "removed_shopping", name)


def _bought_shopping(phone, hid, uid, params, reply, members):
    from datetime import datetime, timezone
    name = params.get("name", "").strip()
    item = find_item_by_name(hid, name)
    if not item:
        send_message(phone, f"לא מצאתי *{name}* ברשימה")
        return
    update_shopping_item(item["id"], {
        "is_bought": True, "bought_by": uid,
        "bought_at": datetime.now(timezone.utc).isoformat(),
    })
    send_confirmation(phone, "bought_shopping", name)


def _list_shopping(phone, hid, uid, params, reply, members):
    send_shopping_list(phone, get_shopping_list(hid, include_bought=False))


def _clear_bought(phone, hid, uid, params, reply, members):
    count = clear_bought_items(hid)
    send_message(phone, f"ניקיתי {count} פריטים שנקנו מהרשימה 🧹")


# ══════════════════════════════════════════════════════════════
# Handlers — חשבונות
# ══════════════════════════════════════════════════════════════

def _add_bill(phone, hid, uid, params, reply, members):
    name = params.get("name", "").strip()
    if not name:
        send_message(phone, "לא הבנתי איזה חשבון לשמור")
        return
    add_bill(
        household_id=hid, name=name,
        amount=params.get("amount") or 0,
        category=params.get("category", "אחר"),
        due_date=params.get("due_date"),
        recurring=params.get("recurring", False),
        recurrence=params.get("recurrence"),
        created_by=uid,
    )
    send_confirmation(phone, "added_bill", name)


def _mark_bill_paid(phone, hid, uid, params, reply, members):
    name  = params.get("name", "").strip()
    match = _find_by_name(get_bills(hid, paid=False), name)
    if not match:
        send_message(phone, f"לא מצאתי חשבון פתוח בשם *{name}*")
        return
    mark_bill_paid(match["id"], paid_by=uid)
    send_confirmation(phone, "paid_bill", match["name"])


def _list_bills(phone, hid, uid, params, reply, members):
    f    = params.get("filter", "unpaid")
    paid = None if f == "all" else (f == "paid")
    send_bills_summary(phone, get_bills(hid, paid=paid))


# ══════════════════════════════════════════════════════════════
# Handlers — משימות
# ══════════════════════════════════════════════════════════════

def _add_task(phone, hid, uid, params, reply, members):
    title = params.get("title", "").strip()
    if not title:
        send_message(phone, "לא הבנתי מה המשימה")
        return
    assigned_id = None
    if params.get("assigned_to_name"):
        m = _find_member_by_name(members, params["assigned_to_name"])
        if m:
            assigned_id = m["id"]
    add_task(
        household_id=hid, title=title,
        description=params.get("description", ""),
        assigned_to=assigned_id, created_by=uid,
        priority=params.get("priority", 0),
        due_date=params.get("due_date"),
    )
    send_confirmation(phone, "added_task", title)


def _list_tasks(phone, hid, uid, params, reply, members):
    f        = params.get("filter", "open")
    assigned = uid if f == "mine" else None
    send_tasks_summary(phone, get_tasks(hid, status="open", assigned_to=assigned))


def _done_task(phone, hid, uid, params, reply, members):
    title = params.get("title", "").strip()
    match = _find_by_name(get_tasks(hid, status="open"), title, key="title")
    if not match:
        send_message(phone, f"לא מצאתי משימה פתוחה בשם *{title}*")
        return
    update_task_status(match["id"], "done")
    send_confirmation(phone, "done_task", match["title"])


# ══════════════════════════════════════════════════════════════
# עזרים
# ══════════════════════════════════════════════════════════════

def _find_by_name(items: list[dict], name: str, key: str = "name") -> dict | None:
    nl = name.lower()
    for item in items:
        if item.get(key, "").lower() == nl:
            return item
    for item in items:
        if nl in item.get(key, "").lower():
            return item
    return None


def _find_member_by_name(members: list[dict], name: str) -> dict | None:
    nl = name.lower()
    for m in members:
        if nl in m.get("name", "").lower():
            return m
    return None
