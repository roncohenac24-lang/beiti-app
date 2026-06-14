"""
services/heyy_service.py
ממשק ל-heyy.io API v2.0 — שליחת הודעות WhatsApp.
Base URL: https://api.hey-y.io/api/v2.0
"""

import os
import requests
from typing import Any

HEYY_BASE = "https://api.hey-y.io/api/v2.0"


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.getenv('HEYY_API_KEY', '')}",
        "Content-Type": "application/json",
    }


def _instance() -> str:
    return os.getenv("HEYY_INSTANCE_ID", "")


def _post(endpoint: str, payload: dict) -> dict[str, Any]:
    url = f"{HEYY_BASE}/{endpoint.lstrip('/')}"
    res = requests.post(url, json=payload, headers=_headers(), timeout=10)
    res.raise_for_status()
    return res.json()


# ══════════════════════════════════════════════════════════════
# שליחת הודעות
# ══════════════════════════════════════════════════════════════

def send_message(to: str, text: str) -> dict:
    """
    שולח הודעת טקסט פשוטה.
    to: מספר בינלאומי ללא + — למשל 972501234567
    """
    return _post("messages/send", {
        "instanceId": _instance(),
        "to": to,
        "message": {"text": text},
    })


def send_buttons(to: str, body: str, buttons: list[str]) -> dict:
    """
    שולח הודעה עם כפתורי תשובה מהירה (עד 3 כפתורים).
    buttons: רשימת מחרוזות — ["כן", "לא", "אחר כך"]
    """
    btn_list = [
        {"type": "reply", "reply": {"id": str(i), "title": label}}
        for i, label in enumerate(buttons[:3])
    ]
    return _post("messages/send", {
        "instanceId": _instance(),
        "to": to,
        "message": {
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {"buttons": btn_list},
            },
        },
    })


def send_list(to: str, header: str, body: str, button_label: str, sections: list[dict]) -> dict:
    """
    שולח הודעת רשימה אינטראקטיבית.
    sections: [{"title": "קטגוריה", "rows": [{"id": "1", "title": "חלב", "description": "2 ליטר"}]}]
    """
    return _post("messages/send", {
        "instanceId": _instance(),
        "to": to,
        "message": {
            "type": "interactive",
            "interactive": {
                "type": "list",
                "header": {"type": "text", "text": header},
                "body": {"text": body},
                "action": {"button": button_label, "sections": sections},
            },
        },
    })


def send_template(to: str, template_name: str, params: list[str], lang: str = "he") -> dict:
    """
    שולח template message — נדרש לפתיחת שיחה לאחר 24 שעות.
    """
    return _post("messages/send", {
        "instanceId": _instance(),
        "to": to,
        "message": {
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": lang},
                "components": [{
                    "type": "body",
                    "parameters": [{"type": "text", "text": p} for p in params],
                }],
            },
        },
    })


# ══════════════════════════════════════════════════════════════
# הודעות מוכנות לביתי
# ══════════════════════════════════════════════════════════════

def send_shopping_list(to: str, items: list[dict]) -> dict:
    """
    שולח את רשימת הקניות בפורמט נקי.
    items: [{"name": "חלב", "quantity": "2 ליטר"}, ...]
    """
    if not items:
        return send_message(to, "הרשימה ריקה כרגע")

    lines = []
    for i, item in enumerate(items, 1):
        qty = f" — {item['quantity']}" if item.get("quantity") else ""
        lines.append(f"{i}. {item['name']}{qty}")

    text = "רשימת הקניות שלך:\n\n" + "\n".join(lines)
    return send_message(to, text)


def send_bills_summary(to: str, bills: list[dict]) -> dict:
    """
    שולח סיכום חשבונות פתוחים.
    bills: [{"name": "חשמל", "amount": 380, "due_date": "2026-07-01"}, ...]
    """
    if not bills:
        return send_message(to, "אין חשבונות פתוחים")

    lines = []
    for b in bills:
        due = f" (עד {b['due_date']})" if b.get("due_date") else ""
        amount = f"₪{b['amount']:.0f}" if b.get("amount") else ""
        lines.append(f"• {b['name']} {amount}{due}")

    text = "חשבונות לתשלום:\n\n" + "\n".join(lines)
    return send_message(to, text)


def send_tasks_summary(to: str, tasks: list[dict]) -> dict:
    """שולח רשימת משימות פתוחות."""
    if not tasks:
        return send_message(to, "אין משימות פתוחות")

    priority_emoji = {0: "⬜", 1: "🟡", 2: "🔴"}
    lines = []
    for t in tasks:
        emoji = priority_emoji.get(t.get("priority", 0), "⬜")
        due = f" — עד {t['due_date']}" if t.get("due_date") else ""
        lines.append(f"{emoji} {t['title']}{due}")

    text = "משימות פתוחות:\n\n" + "\n".join(lines)
    return send_message(to, text)


def send_confirmation(to: str, action: str, item: str) -> dict:
    """הודעת אישור סטנדרטית — "הוספתי חלב לרשימה"."""
    messages = {
        "added_shopping":  f"הוספתי *{item}* לרשימת הקניות",
        "removed_shopping": f"הסרתי *{item}* מהרשימה",
        "bought_shopping":  f"מעולה! סימנתי *{item}* כנקנה",
        "added_bill":       f"שמרתי את החשבון: *{item}*",
        "paid_bill":        f"סימנתי *{item}* כשולם",
        "added_task":       f"הוספתי משימה: *{item}*",
        "done_task":        f"כל הכבוד! סימנתי *{item}* כבוצע",
    }
    text = messages.get(action, f"בוצע: {item}")
    return send_message(to, text)
