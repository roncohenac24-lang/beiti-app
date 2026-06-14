"""
services/supabase_service.py
ממשק מלא ל-Supabase — כל 6 הטבלאות.
משתמש ב-service_role key כדי לעקוף RLS מה-backend.
"""

import os
from typing import Any
from supabase import create_client, Client

_client: Client | None = None


def db() -> Client:
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY חסרים ב-.env")
        _client = create_client(url, key)
    return _client


# ══════════════════════════════════════════════════════════════
# HOUSEHOLDS
# ══════════════════════════════════════════════════════════════

def get_household(household_id: str) -> dict | None:
    res = db().table("households").select("*").eq("id", household_id).maybe_single().execute()
    return res.data


def get_or_create_household_by_phone(phone: str, name: str = "") -> dict:
    """
    מחזיר את ה-household לפי מספר טלפון.
    אם לא קיים — יוצר household חדש ומוסיף את המשתמש.
    """
    user = get_user_by_phone(phone)
    if user:
        hh = db().table("households").select("*").eq("id", user["household_id"]).maybe_single().execute()
        return hh.data

    # משתמש חדש — צור household ואז user
    hh = db().table("households").insert({"name": "ביתי"}).execute()
    household = hh.data[0]
    db().table("users").insert({
        "household_id": household["id"],
        "name": name or phone,
        "phone": phone,
        "role": "admin",
    }).execute()
    return household


def update_household(household_id: str, fields: dict) -> dict:
    res = db().table("households").update(fields).eq("id", household_id).execute()
    return res.data[0]


# ══════════════════════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════════════════════

def get_user_by_phone(phone: str) -> dict | None:
    res = db().table("users").select("*").eq("phone", phone).execute()
    return res.data[0] if res.data else None


def get_household_members(household_id: str) -> list[dict]:
    res = (
        db().table("users")
        .select("*")
        .eq("household_id", household_id)
        .eq("is_active", True)
        .execute()
    )
    return res.data or []


def add_member(household_id: str, name: str, phone: str, role: str = "member") -> dict:
    res = db().table("users").insert({
        "household_id": household_id,
        "name": name,
        "phone": phone,
        "role": role,
    }).execute()
    return res.data[0]


def update_user(user_id: str, fields: dict) -> dict:
    res = db().table("users").update(fields).eq("id", user_id).execute()
    return res.data[0]


def deactivate_user(user_id: str) -> None:
    db().table("users").update({"is_active": False}).eq("id", user_id).execute()


# ══════════════════════════════════════════════════════════════
# SHOPPING LIST
# ══════════════════════════════════════════════════════════════

def get_shopping_list(household_id: str, include_bought: bool = False) -> list[dict]:
    query = (
        db().table("shopping_list")
        .select("*")
        .eq("household_id", household_id)
    )
    if not include_bought:
        query = query.eq("is_bought", False)
    res = query.order("priority", desc=True).order("created_at").execute()
    return res.data or []


def add_shopping_item(
    household_id: str,
    name: str,
    quantity: str = "",
    category: str = "כללי",
    added_by: str | None = None,
    priority: int = 0,
    notes: str = "",
) -> dict:
    res = db().table("shopping_list").insert({
        "household_id": household_id,
        "name": name,
        "quantity": quantity,
        "category": category,
        "added_by": added_by,
        "priority": priority,
        "notes": notes,
        "is_bought": False,
    }).execute()
    return res.data[0]


def mark_item_bought(item_id: str, bought_by: str | None = None) -> dict:
    from datetime import datetime, timezone
    res = db().table("shopping_list").update({
        "is_bought": True,
        "bought_by": bought_by,
        "bought_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", item_id).execute()
    return res.data[0]


def update_shopping_item(item_id: str, fields: dict) -> dict:
    res = db().table("shopping_list").update(fields).eq("id", item_id).execute()
    return res.data[0]


def delete_shopping_item(item_id: str) -> None:
    db().table("shopping_list").delete().eq("id", item_id).execute()


def clear_bought_items(household_id: str) -> int:
    res = (
        db().table("shopping_list")
        .delete()
        .eq("household_id", household_id)
        .eq("is_bought", True)
        .execute()
    )
    return len(res.data) if res.data else 0


def find_item_by_name(household_id: str, name: str) -> dict | None:
    res = (
        db().table("shopping_list")
        .select("*")
        .eq("household_id", household_id)
        .eq("is_bought", False)
        .ilike("name", f"%{name}%")
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


# ══════════════════════════════════════════════════════════════
# BILLS
# ══════════════════════════════════════════════════════════════

def get_bills(
    household_id: str,
    paid: bool | None = None,
    category: str | None = None,
) -> list[dict]:
    query = db().table("bills").select("*").eq("household_id", household_id)
    if paid is not None:
        query = query.eq("is_paid", paid)
    if category:
        query = query.eq("category", category)
    res = query.order("due_date").execute()
    return res.data or []


def get_upcoming_bills(household_id: str, days: int = 7) -> list[dict]:
    from datetime import date, timedelta
    today  = date.today().isoformat()
    future = (date.today() + timedelta(days=days)).isoformat()
    res = (
        db().table("bills")
        .select("*")
        .eq("household_id", household_id)
        .eq("is_paid", False)
        .gte("due_date", today)
        .lte("due_date", future)
        .order("due_date")
        .execute()
    )
    return res.data or []


def add_bill(
    household_id: str,
    name: str,
    amount: float = 0,
    category: str = "אחר",
    due_date: str | None = None,
    recurring: bool = False,
    recurrence: str | None = None,
    created_by: str | None = None,
    notes: str = "",
) -> dict:
    res = db().table("bills").insert({
        "household_id": household_id,
        "name": name,
        "amount": amount,
        "category": category,
        "due_date": due_date,
        "recurring": recurring,
        "recurrence": recurrence,
        "created_by": created_by,
        "notes": notes,
        "is_paid": False,
    }).execute()
    return res.data[0]


def mark_bill_paid(bill_id: str, paid_by: str | None = None) -> dict:
    from datetime import datetime, timezone
    res = db().table("bills").update({
        "is_paid": True,
        "paid_by": paid_by,
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", bill_id).execute()
    return res.data[0]


def update_bill(bill_id: str, fields: dict) -> dict:
    res = db().table("bills").update(fields).eq("id", bill_id).execute()
    return res.data[0]


def delete_bill(bill_id: str) -> None:
    db().table("bills").delete().eq("id", bill_id).execute()


# ══════════════════════════════════════════════════════════════
# TASKS
# ══════════════════════════════════════════════════════════════

def get_tasks(
    household_id: str,
    status: str | None = None,
    assigned_to: str | None = None,
) -> list[dict]:
    query = db().table("tasks").select("*").eq("household_id", household_id)
    if status:
        query = query.eq("status", status)
    if assigned_to:
        query = query.eq("assigned_to", assigned_to)
    res = query.order("priority", desc=True).order("created_at").execute()
    return res.data or []


def add_task(
    household_id: str,
    title: str,
    description: str = "",
    assigned_to: str | None = None,
    created_by: str | None = None,
    priority: int = 0,
    due_date: str | None = None,
    recurring: bool = False,
    recurrence: str | None = None,
) -> dict:
    res = db().table("tasks").insert({
        "household_id": household_id,
        "title": title,
        "description": description,
        "assigned_to": assigned_to,
        "created_by": created_by,
        "priority": priority,
        "due_date": due_date,
        "recurring": recurring,
        "recurrence": recurrence,
        "status": "open",
    }).execute()
    return res.data[0]


def update_task_status(task_id: str, status: str) -> dict:
    from datetime import datetime, timezone
    fields: dict[str, Any] = {"status": status}
    if status == "done":
        fields["completed_at"] = datetime.now(timezone.utc).isoformat()
    res = db().table("tasks").update(fields).eq("id", task_id).execute()
    return res.data[0]


def update_task(task_id: str, fields: dict) -> dict:
    res = db().table("tasks").update(fields).eq("id", task_id).execute()
    return res.data[0]


def delete_task(task_id: str) -> None:
    db().table("tasks").delete().eq("id", task_id).execute()


# ══════════════════════════════════════════════════════════════
# PURCHASE HISTORY
# ══════════════════════════════════════════════════════════════

def get_frequent_items(household_id: str, limit: int = 20) -> list[dict]:
    res = (
        db().table("purchase_history")
        .select("normalized_name, category, times_bought, last_bought_at")
        .eq("household_id", household_id)
        .order("times_bought", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []


def get_recent_purchases(household_id: str, limit: int = 10) -> list[dict]:
    res = (
        db().table("purchase_history")
        .select("*")
        .eq("household_id", household_id)
        .order("last_bought_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data or []
