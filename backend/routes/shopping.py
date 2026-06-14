"""
routes/shopping.py
==================
CRUD לרשימת הקניות של הבית.
כל בית (household) מנהל רשימה משלו ב-Supabase.

Endpoints:
  GET    /shopping/<household_id>         - קבל את כל הפריטים
  POST   /shopping/<household_id>         - הוסף פריט
  PATCH  /shopping/<household_id>/<item_id> - עדכן פריט (נקנה / כמות)
  DELETE /shopping/<household_id>/<item_id> - הסר פריט
"""

from flask import Blueprint, request, jsonify
from services.supabase_service import (
    get_shopping_list,
    add_shopping_item,
    update_shopping_item,
    delete_shopping_item,
)

shopping_bp = Blueprint("shopping", __name__)


@shopping_bp.route("/<household_id>", methods=["GET"])
def list_items(household_id):
    """החזר את רשימת הקניות הפעילה."""
    items = get_shopping_list(household_id)
    return jsonify({"items": items}), 200


@shopping_bp.route("/<household_id>", methods=["POST"])
def add_item(household_id):
    """
    הוסף פריט לרשימה.
    Body: { "name": "חלב", "quantity": "2 ליטר", "added_by": "רון" }
    """
    body = request.get_json(silent=True) or {}
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    item = add_shopping_item(
        household_id=household_id,
        name=name,
        quantity=body.get("quantity", ""),
        added_by=body.get("added_by", ""),
    )
    return jsonify({"item": item}), 201


@shopping_bp.route("/<household_id>/<item_id>", methods=["PATCH"])
def update_item(household_id, item_id):
    """עדכן פריט — סמן כנקנה, שנה כמות וכו'."""
    body = request.get_json(silent=True) or {}
    updated = update_shopping_item(household_id, item_id, body)
    return jsonify({"item": updated}), 200


@shopping_bp.route("/<household_id>/<item_id>", methods=["DELETE"])
def remove_item(household_id, item_id):
    """מחק פריט מהרשימה."""
    delete_shopping_item(household_id, item_id)
    return jsonify({"ok": True}), 200
