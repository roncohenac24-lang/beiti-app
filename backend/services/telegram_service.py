"""
services/telegram_service.py
שליחת הודעות דרך Telegram Bot API.
משתמש ב-python-telegram-bot v21 (async) עם asyncio.run() מ-Flask sync.
"""

import asyncio
import os
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

def _bot() -> Bot:
    return Bot(token=os.getenv("TELEGRAM_BOT_TOKEN", ""))


def _run(coro):
    return asyncio.run(coro)


# ══════════════════════════════════════════════════════════════
# פונקציות שליחה בסיסיות
# ══════════════════════════════════════════════════════════════

def send_message(to: str, text: str) -> None:
    async def _send():
        async with _bot() as bot:
            await bot.send_message(chat_id=to, text=text, parse_mode="Markdown")
    _run(_send())


def send_buttons(to: str, body: str, buttons: list[str]) -> None:
    """שולח הודעה עם כפתורי Inline Keyboard (עד 3)."""
    keyboard = [[InlineKeyboardButton(b, callback_data=b)] for b in buttons[:3]]
    markup = InlineKeyboardMarkup(keyboard)

    async def _send():
        async with _bot() as bot:
            await bot.send_message(
                chat_id=to, text=body,
                parse_mode="Markdown",
                reply_markup=markup,
            )
    _run(_send())


def send_list(to: str, header: str, body: str, button_label: str, sections: list[dict]) -> None:
    """Telegram אין list message — שולח כטקסט מעוצב."""
    lines = [f"*{header}*", ""]
    for section in sections:
        if section.get("title"):
            lines.append(f"_{section['title']}_")
        for row in section.get("rows", []):
            desc = f" — {row['description']}" if row.get("description") else ""
            lines.append(f"• {row['title']}{desc}")
    send_message(to, "\n".join(lines))


# ══════════════════════════════════════════════════════════════
# הודעות מוכנות לביתי
# ══════════════════════════════════════════════════════════════

def send_shopping_list(to: str, items: list[dict]) -> None:
    if not items:
        send_message(to, "הרשימה ריקה כרגע")
        return

    lines = ["*רשימת הקניות:*", ""]
    for i, item in enumerate(items, 1):
        qty      = f" — {item['quantity']}" if item.get("quantity") else ""
        urgent   = " 🔴" if item.get("priority") == 1 else ""
        lines.append(f"{i}\\. {item['name']}{qty}{urgent}")

    send_message(to, "\n".join(lines))


def send_bills_summary(to: str, bills: list[dict]) -> None:
    if not bills:
        send_message(to, "אין חשבונות פתוחים")
        return

    lines = ["*חשבונות לתשלום:*", ""]
    for b in bills:
        amount = f" ₪{b['amount']:.0f}" if b.get("amount") else ""
        due    = f" _(עד {b['due_date']})_" if b.get("due_date") else ""
        lines.append(f"• {b['name']}{amount}{due}")

    send_message(to, "\n".join(lines))


def send_tasks_summary(to: str, tasks: list[dict]) -> None:
    if not tasks:
        send_message(to, "אין משימות פתוחות")
        return

    icons = {0: "⬜", 1: "🟡", 2: "🔴"}
    lines = ["*משימות פתוחות:*", ""]
    for t in tasks:
        icon = icons.get(t.get("priority", 0), "⬜")
        due  = f" _(עד {t['due_date']})_" if t.get("due_date") else ""
        lines.append(f"{icon} {t['title']}{due}")

    send_message(to, "\n".join(lines))


def send_confirmation(to: str, action: str, item: str) -> None:
    messages = {
        "added_shopping":   f"הוספתי *{item}* לרשימת הקניות ✅",
        "removed_shopping": f"הסרתי *{item}* מהרשימה 🗑",
        "bought_shopping":  f"סימנתי *{item}* כנקנה ✅",
        "added_bill":       f"שמרתי את החשבון: *{item}* 📋",
        "paid_bill":        f"סימנתי *{item}* כשולם ✅",
        "added_task":       f"הוספתי משימה: *{item}* 📝",
        "done_task":        f"סימנתי *{item}* כבוצע ✅",
    }
    send_message(to, messages.get(action, f"בוצע: {item}"))
