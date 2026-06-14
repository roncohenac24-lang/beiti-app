"""
routes/bills.py
===============
ניהול חשבונות ותשלומים של הבית.
כל חשבון שייך ל-household, יכול להיות חוזר (חשמל/מים/ארנונה)
או חד-פעמי.

Endpoints:
  GET    /bills/<household_id>          - כל החשבונות
  POST   /bills/<household_id>          - צור חשבון חדש
  PATCH  /bills/<household_id>/<bill_id> - עדכן / סמן כשולם
  DELETE /bills/<household_id>/<bill_id> - מחק
"""

from flask import Blueprint, request, jsonify
from services.supabase_service import (
    get_bills,
    add_bill,
    update_bill,
    delete_bill,
)

bills_bp = Blueprint("bills", __name__)


@bills_bp.route("/<household_id>", methods=["GET"])
def list_bills(household_id):
    """החזר את כל החשבונות — אפשר לסנן ?paid=false."""
    paid_filter = request.args.get("paid")  # "true" / "false" / None
    bills = get_bills(household_id, paid_filter=paid_filter)
    return jsonify({"bills": bills}), 200


@bills_bp.route("/<household_id>", methods=["POST"])
def create_bill(household_id):
    """
    צור חשבון חדש.
    Body:
    {
        "name": "חשמל",
        "amount": 350.0,
        "due_date": "2026-07-01",
        "recurring": true,
        "notes": "חברת חשמל"
    }
    """
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    bill = add_bill(
        household_id=household_id,
        name=name,
        amount=body.get("amount", 0),
        due_date=body.get("due_date"),
        recurring=body.get("recurring", False),
        notes=body.get("notes", ""),
    )
    return jsonify({"bill": bill}), 201


@bills_bp.route("/<household_id>/<bill_id>", methods=["PATCH"])
def update_bill_route(household_id, bill_id):
    """עדכן חשבון — למשל סמן paid=true."""
    body = request.get_json(silent=True) or {}
    updated = update_bill(household_id, bill_id, body)
    return jsonify({"bill": updated}), 200


@bills_bp.route("/<household_id>/<bill_id>", methods=["DELETE"])
def remove_bill(household_id, bill_id):
    delete_bill(household_id, bill_id)
    return jsonify({"ok": True}), 200
