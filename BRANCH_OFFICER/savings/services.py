"""BRANCH_OFFICER Savings page service. Own page only."""
from __future__ import annotations
from datetime import datetime, timezone
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("branch_officer_database_savings", Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py")
db = importlib.util.module_from_spec(spec); spec.loader.exec_module(db)
ROLE = "BRANCH_OFFICER"
COLLECTION = 'savings'

def _branch(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")
    branch_id = str(context.get("branch_id") or "").strip()
    if not branch_id:
        raise PermissionError("A branch assignment is required.")
    return branch_id

def list_records(context, filters=None):
    branch_id = _branch(context)
    filters = filters or {}
    client, database = db.get_mongo()
    try:
        query = {"branch_id": branch_id}
        search = str(filters.get("search") or "").strip()
        if search:
            query["$or"] = [
                {"note": {"$regex": search, "$options":"i"}},
                {"source": {"$regex": search, "$options":"i"}},
                {"purpose": {"$regex": search, "$options":"i"}},
                {"member_name": {"$regex": search, "$options":"i"}},
                {"task_title": {"$regex": search, "$options":"i"}},
                {"work_id": {"$regex": search, "$options":"i"}},
            ]
        date = str(filters.get("date") or "").strip()
        month = str(filters.get("month") or "").strip()
        if date:
            query["date"] = date
        elif month:
            query["date"] = {"$regex": f"^{month}"}
        member = str(filters.get("member") or "").strip()
        if member:
            query["member_name"] = {"$regex": member, "$options":"i"}
        cursor = database[COLLECTION].find(query).sort("created_at",-1).limit(300)
        rows=[]
        for row in cursor:
            row["_id"]=str(row["_id"])
            rows.append(row)
        return rows
    finally:
        client.close()

def create_record(context, data):
    branch_id = _branch(context)
    payload = {k:v for k,v in dict(data or {}).items() if k not in ("branch_id","created_by","created_at","updated_at")}
    payload["branch_id"] = branch_id
    payload["created_by"] = context.get("user_id")
    payload["created_at"] = datetime.now(timezone.utc)
    client, database = db.get_mongo()
    try:
        result = database[COLLECTION].insert_one(payload)
        return str(result.inserted_id)
    finally:
        client.close()

def update_record(context, record_id, data):
    branch_id = _branch(context)
    from bson import ObjectId
    payload = {k:v for k,v in dict(data or {}).items() if k not in ("branch_id","created_by","created_at")}
    payload["updated_at"] = datetime.now(timezone.utc)
    client, database = db.get_mongo()
    try:
        result = database[COLLECTION].update_one({"_id":ObjectId(record_id),"branch_id":branch_id}, {"$set":payload})
        return result.modified_count > 0
    finally:
        client.close()

def delete_record(context, record_id):
    branch_id = _branch(context)
    from bson import ObjectId
    client, database = db.get_mongo()
    try:
        result = database[COLLECTION].delete_one({"_id":ObjectId(record_id),"branch_id":branch_id})
        return result.deleted_count > 0
    finally:
        client.close()
