"""ACCOUNTS OFFICER — Expense page service. This file belongs only to this page."""
from datetime import datetime, timezone
from bson import ObjectId
from pathlib import Path
import importlib.util

ROLE = "ACCOUNT_OFFICER"
PAGE = "expense"
COLLECTION_NAME = "accounts_officer_expense"

_spec = importlib.util.spec_from_file_location(
    "accounts_officer_expense_database",
    Path(__file__).resolve().parents[1] / "config" / "accounts_officer_database.py"
)
_db = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_db)

def _scope(context):
    return {
        "role": ROLE,
        "user_id": context.get("user_id"),
        "branch_id": context.get("branch_id"),
        "section_id": context.get("section_id"),
    }

def authorized(context):
    return isinstance(context, dict) and context.get("role") == ROLE

def list_records(context, filters=None):
    if not authorized(context):
        raise PermissionError("Accounts Officer access required.")
    if not COLLECTION_NAME:
        return []
    client, db = _db.get_mongo()
    try:
        query = {}
        scope = _scope(context)
        if scope["branch_id"]:
            query["branch_id"] = scope["branch_id"]
        if scope["section_id"]:
            query["section_id"] = scope["section_id"]
        return list(db[COLLECTION_NAME].find(query).sort("created_at", -1).limit(100))
    finally:
        client.close()

def save_record(context, data):
    if not authorized(context):
        raise PermissionError("Accounts Officer access required.")
    if not COLLECTION_NAME:
        return {"ok": False, "error": "This page is view-only."}
    payload = dict(data or {})
    payload.update({"role": ROLE, "updated_at": datetime.now(timezone.utc)})
    scope = _scope(context)
    payload.update({k:v for k,v in scope.items() if v})
    client, db = _db.get_mongo()
    try:
        result = db[COLLECTION_NAME].insert_one(payload)
        return {"ok": True, "id": str(result.inserted_id)}
    finally:
        client.close()

def delete_record(context, record_id):
    if not authorized(context):
        raise PermissionError("Accounts Officer access required.")
    if not COLLECTION_NAME:
        return {"ok": False, "error": "This page is view-only."}
    client, db = _db.get_mongo()
    try:
        result = db[COLLECTION_NAME].delete_one({"_id": ObjectId(str(record_id)), "role": ROLE})
        return {"ok": result.deleted_count == 1}
    finally:
        client.close()
