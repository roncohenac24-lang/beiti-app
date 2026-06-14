"""
services/claude_service.py
ממשק ל-Claude API — הבנת הודעות WhatsApp בעברית והחזרת intent מובנה.
"""

import json
import os
import re
from typing import Any

import anthropic

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        key = os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY חסר ב-.env")
        _client = anthropic.Anthropic(api_key=key)
    return _client


# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """
אתה "ביתי" — עוזר בית חכם שמנהל קניות, חשבונות ומשימות דרך WhatsApp.
אתה מקבל הודעות בעברית ומחזיר תמיד JSON תקין בלבד, ללא שום טקסט נוסף.

## מבנה התשובה (JSON בלבד):
{
  "intent": "<intent>",
  "params": { <פרמטרים לפי intent> },
  "reply": "<תשובה קצרה וידידותית בעברית למשתמש>"
}

## Intents אפשריים:

### רשימת קניות:
- "add_shopping"     → params: { "name": string, "quantity": string, "category": string, "priority": 0|1 }
- "remove_shopping"  → params: { "name": string }
- "bought_shopping"  → params: { "name": string }
- "list_shopping"    → params: {}
- "clear_bought"     → params: {}

### חשבונות:
- "add_bill"         → params: { "name": string, "amount": number|null, "category": string, "due_date": "YYYY-MM-DD"|null, "recurring": bool, "recurrence": "monthly"|"bimonthly"|"yearly"|null }
- "mark_bill_paid"   → params: { "name": string }
- "list_bills"       → params: { "filter": "all"|"unpaid"|"paid" }

### משימות:
- "add_task"         → params: { "title": string, "description": string, "assigned_to_name": string|null, "priority": 0|1|2, "due_date": "YYYY-MM-DD"|null }
- "list_tasks"       → params: { "filter": "all"|"mine"|"open" }
- "done_task"        → params: { "title": string }

### כללי:
- "general"          → params: {}

## כללים:
- category לקניות: "מוצרי חלב" | "ירקות ופירות" | "בשר ודגים" | "מאפים" | "שימורים" | "ניקיון" | "היגיינה" | "קפואים" | "משקאות" | "כללי"
- category לחשבונות: "חשמל" | "מים" | "גז" | "ארנונה" | "ועד בית" | "אינטרנט" | "ביטוח" | "שכירות" | "אחר"
- תאריכים: המר "ל-15 ליולי" → "2026-07-15", "חודש הבא" → תאריך מוחשי, "מחר" → מחר וכו'
- אם כמות לא ציינו — quantity: ""
- אם סכום לא ציין — amount: null
- reply: משפט אחד קצר, ידידותי, בגוף שני
- אל תוסיף ```json או שום עטיפה — JSON גולמי בלבד
""".strip()


# ─── פונקציה ראשית ────────────────────────────────────────────────────────────

def understand_message(
    text: str,
    sender_name: str = "",
    household_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    מנתח הודעת WhatsApp ומחזיר:
      { intent, params, reply }

    household_context: מידע אופציונלי על הבית (חברים, פריטים קיימים וכו')
    לשיפור הדיוק של Claude.
    """
    user_content = _build_user_content(text, sender_name, household_context)

    response = _get_client().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    raw = response.content[0].text.strip()
    return _parse_response(raw)


def _build_user_content(
    text: str,
    sender_name: str,
    context: dict[str, Any] | None,
) -> str:
    parts = []

    if sender_name:
        parts.append(f"שם השולח: {sender_name}")

    if context:
        members = context.get("members", [])
        if members:
            names = ", ".join(m["name"] for m in members)
            parts.append(f"בני הבית: {names}")

    parts.append(f"הודעה: {text}")
    return "\n".join(parts)


def _parse_response(raw: str) -> dict[str, Any]:
    """מנתח JSON מהתשובה — מטפל גם בעטיפות markdown."""
    # הסר עטיפות ```json ... ```
    clean = re.sub(r"```(?:json)?\s*|\s*```", "", raw).strip()

    try:
        result = json.loads(clean)
        # וידוא מינימלי
        result.setdefault("intent", "general")
        result.setdefault("params", {})
        result.setdefault("reply", "אוקיי!")
        return result
    except json.JSONDecodeError:
        # אם Claude החזיר טקסט חופשי — treat as general
        return {
            "intent": "general",
            "params": {},
            "reply": raw[:200],  # חתוך אם ארוך מדי
        }
