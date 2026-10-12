"""Standalone Daily Bazar List service layer.

Only this module handles persistence for the Daily Bazar page.
It intentionally does not modify the existing Meal Management collection.
"""
from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
COLLECTION = "daily_bazar_list"


def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")


def _oid(value):
    value = str(value or "").strip()
    if not ObjectId.is_valid(value):
        raise ValueError("Invalid bazar record ID.")
    return ObjectId(value)


def _money(value, field):
    try:
        amount = round(float(value or 0), 2)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a valid number.")
    if amount < 0:
        raise ValueError(f"{field} cannot be negative.")
    return amount


def _prepare(data):
    data = dict(data or {})
    bazar_date = str(data.get("bazar_date", "")).strip()
    member_id = str(data.get("member_id", "")).strip()
    member_name = str(data.get("member_name", "")).strip()
    member_mobile = str(data.get("member_mobile", "")).strip()
    if not bazar_date:
        raise ValueError("Please select the bazar date.")
    if not member_id or not member_name:
        raise ValueError("Please select a Member.")

    raw_items = data.get("items", [])
    if not isinstance(raw_items, list):
        raise ValueError("Invalid product list.")
    items, total = [], 0.0
    for row in raw_items:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        try:
            quantity = float(row.get("quantity") or 0)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for {name}.")
        if quantity <= 0:
            raise ValueError(f"Quantity for {name} must be greater than zero.")
        unit = str(row.get("unit", "unit")).strip() or "unit"
        rate = _money(row.get("rate"), f"Rate for {name}")
        line_total = round(quantity * rate, 2)
        total += line_total
        items.append({
            "name": name, "quantity": quantity, "unit": unit,
            "rate": rate, "total": line_total
        })
    if not items:
        raise ValueError("Please add at least one product with quantity and price.")

    total = round(total, 2)
    paid = _money(data.get("paid_amount"), "Paid amount")
    difference = round(paid - total, 2)
    note = str(data.get("note", "")).strip()
    return {
        "bazar_date": bazar_date,
        "member_id": member_id,
        "member_name": member_name,
        "member_mobile": member_mobile,
        "items": items,
        "total_amount": total,
        "paid_amount": paid,
        "difference_amount": difference,
        "note": note,
    }


def list_members(context):
    _guard(context)
    db = get_database()
    members = []
    seen = set()
    cursor = db["users"].find({
        "role": {"$regex": "^MEMBER$", "$options": "i"},
        "status": {"$nin": ["Inactive", "inactive", "Disabled", "disabled"]}
    })
    for user in cursor:
        uid = str(user.get("_id", ""))
        name = str(user.get("full_name") or user.get("name") or user.get("username") or "").strip()
        mobile = str(user.get("mobile") or user.get("phone") or user.get("mobile_number") or "").strip()
        if not uid or not name or uid in seen:
            continue
        seen.add(uid)
        members.append({"id": uid, "name": name, "mobile": mobile,
                        "username": str(user.get("username") or "")})
    members.sort(key=lambda x: x["name"].casefold())
    return members


def list_records(context, filters=None, limit=500):
    _guard(context)
    filters = filters or {}
    query = {}
    bazar_date = str(filters.get("date") or "").strip()
    month = str(filters.get("month") or "").strip()
    member = str(filters.get("member") or "").strip()
    search = str(filters.get("search") or "").strip()
    if bazar_date:
        query["bazar_date"] = bazar_date
    elif month:
        query["bazar_date"] = {"$regex": "^" + month}
    if member:
        query["member_id"] = member
    if search:
        query["$or"] = [
            {"member_name": {"$regex": search, "$options": "i"}},
            {"member_mobile": {"$regex": search, "$options": "i"}},
            {"note": {"$regex": search, "$options": "i"}},
            {"items.name": {"$regex": search, "$options": "i"}},
        ]
    records = []
    for row in get_database()[COLLECTION].find(query).sort(
            [("bazar_date", -1), ("created_at", -1)]).limit(max(1, min(int(limit), 2000))):
        row["id"] = str(row.pop("_id"))
        records.append(row)
    return records


def get_record(context, record_id):
    _guard(context)
    row = get_database()[COLLECTION].find_one({"_id": _oid(record_id)})
    if not row:
        raise ValueError("Bazar entry was not found.")
    row["id"] = str(row.pop("_id"))
    return row


def create_record(context, data):
    _guard(context)
    item = _prepare(data)
    now = datetime.now(timezone.utc)
    item.update({"created_at": now, "updated_at": now,
                 "created_by": str(context.get("user_id") or ""),
                 "created_by_role": ROLE})
    result = get_database()[COLLECTION].insert_one(item)
    return str(result.inserted_id)


def update_record(context, record_id, data):
    _guard(context)
    item = _prepare(data)
    item["updated_at"] = datetime.now(timezone.utc)
    result = get_database()[COLLECTION].update_one(
        {"_id": _oid(record_id)}, {"$set": item})
    if result.matched_count == 0:
        raise ValueError("Bazar entry was not found.")
    return True


def delete_record(context, record_id):
    _guard(context)
    result = get_database()[COLLECTION].delete_one({"_id": _oid(record_id)})
    if result.deleted_count == 0:
        raise ValueError("Bazar entry was not found.")
    return True
