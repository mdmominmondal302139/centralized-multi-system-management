"""BRANCH_OFFICER Work page service: branch + member control + assigned work."""
from __future__ import annotations
from datetime import datetime, timezone
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("branch_officer_database_work", Path(__file__).resolve().parents[1]/"config"/"branch_officer_database.py")
db = importlib.util.module_from_spec(spec); spec.loader.exec_module(db)
ROLE = "BRANCH_OFFICER"
COLLECTION = "works"


def _branch(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")
    branch_id = str(context.get("branch_id") or "").strip()
    if not branch_id:
        raise PermissionError("A branch assignment is required.")
    return branch_id


def _context_branch(context):
    return _branch(context)


def branch_overview(context):
    branch_id = _context_branch(context)
    client, database = db.get_mongo()
    try:
        branch = database["branches"].find_one({"_id": _object_id(branch_id)}) if _object_id_valid(branch_id) else database["branches"].find_one({"_id": branch_id})
        if not branch:
            branch = database["branches"].find_one({"id": branch_id})
        member_count = database["members"].count_documents({"branch_id": branch_id})
        active_count = database["members"].count_documents({"branch_id": branch_id, "$or":[{"active":True},{"status":{"$in":["Active","active"]}}]})
        return {
            "branch_id": branch_id,
            "name": (branch or {}).get("name") or (branch or {}).get("branch_name") or branch_id,
            "source_name": (branch or {}).get("source_name", ""),
            "branch_type": (branch or {}).get("branch_type", ""),
            "status": (branch or {}).get("status", "Active"),
            "branch_admin": (branch or {}).get("branch_admin", ""),
            "address": (branch or {}).get("address", ""),
            "phone": (branch or {}).get("phone", ""),
            "email": (branch or {}).get("email", ""),
            "description": (branch or {}).get("description", ""),
            "member_count": member_count,
            "active_member_count": active_count,
        }
    finally:
        client.close()


def list_members(context, search="", status=""):
    branch_id = _context_branch(context)
    client, database = db.get_mongo()
    try:
        query = {"branch_id": branch_id}
        term = str(search or "").strip()
        if term:
            query["$or"] = [
                {"name":{"$regex":term,"$options":"i"}},
                {"username":{"$regex":term,"$options":"i"}},
                {"mobile":{"$regex":term,"$options":"i"}},
                {"email":{"$regex":term,"$options":"i"}},
                {"member_id":{"$regex":term,"$options":"i"}},
            ]
        clean_status = str(status or "").strip()
        if clean_status:
            query["status"] = clean_status
        rows=[]
        for row in database["members"].find(query).sort("name",1).limit(500):
            row["_id"] = str(row["_id"])
            rows.append(row)
        return rows
    finally:
        client.close()


def update_member(context, member_id, data):
    branch_id = _context_branch(context)
    from bson import ObjectId
    try:
        oid = ObjectId(str(member_id))
    except Exception as exc:
        raise ValueError("Invalid member ID.") from exc
    allowed = ("name","mobile","email","sex","date_of_birth","blood_group","occupation","department","present_address","permanent_address","status","active")
    payload = {k:str(data.get(k,"" )).strip() for k in allowed if k in data}
    if "status" in payload and payload["status"] not in {"Active","Inactive"}:
        raise ValueError("Invalid member status.")
    if "status" in payload:
        payload["active"] = payload["status"] == "Active"
    if "active" in payload and isinstance(data.get("active"), bool):
        payload["active"] = data.get("active")
        payload["status"] = "Active" if payload["active"] else "Inactive"
    payload["updated_at"] = datetime.now(timezone.utc)
    client, database = db.get_mongo()
    try:
        result = database["members"].update_one({"_id":oid,"branch_id":branch_id,"role":"MEMBER"},{"$set":payload})
        return result.modified_count > 0 or result.matched_count > 0
    finally:
        client.close()



def update_branch(context, data):
    branch_id = _branch(context)
    allowed = ("name","branch_name","branch_type","source_name","status","address","phone","email","description")
    payload = {k: str(data.get(k, "")).strip() for k in allowed if k in data}
    if "status" in payload and payload["status"] not in {"Active","Inactive","Locked","Open"}:
        raise ValueError("Invalid branch status.")
    if not payload:
        raise ValueError("No branch information was supplied.")
    payload["updated_at"] = datetime.now(timezone.utc)
    client, database = db.get_mongo()
    try:
        oid = _object_id(branch_id) if _object_id_valid(branch_id) else branch_id
        result = database["branches"].update_one({"_id": oid}, {"$set": payload})
        if result.matched_count == 0:
            result = database["branches"].update_one({"id": branch_id}, {"$set": payload})
        return result.modified_count > 0 or result.matched_count > 0
    finally:
        client.close()


def create_member(context, data):
    branch_id = _branch(context)
    from werkzeug.security import generate_password_hash
    name = str(data.get("name", "")).strip()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if not name or not username or not password:
        raise ValueError("Member name, username and password are required.")
    if len(password) < 6:
        raise ValueError("Member password must be at least 6 characters.")
    client, database = db.get_mongo()
    try:
        c = database["members"]
        if c.find_one({"username": username}):
            raise ValueError("Username already exists.")
        email = str(data.get("email", "")).strip()
        if email and c.find_one({"email": email}):
            raise ValueError("Email already exists.")
        now = datetime.now(timezone.utc)
        doc = {
            "name": name, "username": username,
            "password_hash": generate_password_hash(password),
            "role": "MEMBER", "power": "MEMBER", "active": True,
            "status": "Active", "branch_id": branch_id,
            "created_at": now, "updated_at": now,
        }
        for key in ("mobile","email","sex","date_of_birth","blood_group","occupation","department","present_address","permanent_address"):
            value = str(data.get(key, "")).strip()
            if value: doc[key] = value
        r = c.insert_one(doc)
        return str(r.inserted_id)
    finally:
        client.close()


def delete_member(context, member_id):
    branch_id = _branch(context)
    from bson import ObjectId
    try:
        oid = ObjectId(str(member_id))
    except Exception as exc:
        raise ValueError("Invalid member ID.") from exc
    client, database = db.get_mongo()
    try:
        result = database["members"].delete_one({"_id": oid, "branch_id": branch_id, "role": "MEMBER"})
        if result.deleted_count == 0:
            raise ValueError("Member not found in your assigned Branch.")
        return True
    finally:
        client.close()


def reset_member_password(context, member_id, password):
    branch_id = _branch(context)
    from bson import ObjectId
    from werkzeug.security import generate_password_hash
    password = str(password or "")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    try:
        oid = ObjectId(str(member_id))
    except Exception as exc:
        raise ValueError("Invalid member ID.") from exc
    client, database = db.get_mongo()
    try:
        result = database["members"].update_one(
            {"_id": oid, "branch_id": branch_id, "role": "MEMBER"},
            {"$set": {"password_hash": generate_password_hash(password), "updated_at": datetime.now(timezone.utc), "force_password_change": False}}
        )
        if result.matched_count == 0:
            raise ValueError("Member not found in your assigned Branch.")
        return True
    finally:
        client.close()

def _object_id_valid(value):
    try:
        from bson import ObjectId
        return ObjectId.is_valid(str(value))
    except Exception:
        return False


def _object_id(value):
    from bson import ObjectId
    return ObjectId(str(value))


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
        status = str(filters.get("status") or "").strip()
        priority = str(filters.get("priority") or "").strip()
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
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


"""BRANCH_OFFICER Branch Members service; every operation is scoped by assigned branch_id."""
list_members=list_members
create_member=create_member
update_member=update_member
delete_member=delete_member
reset_member_password=reset_member_password
