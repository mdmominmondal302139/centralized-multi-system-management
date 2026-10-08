from __future__ import annotations

from datetime import datetime, timezone
from bson import ObjectId
from DATABASE.mongodb import get_database, clean

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"

SECTIONS = [
    ("dashboard", "Access Dashboard"),
    ("roles", "Role Management"),
    ("permissions", "Permission Management"),
    ("matrix", "Role Permission Matrix"),
    ("users", "User Access"),
    ("pages", "Page Access"),
    ("modules", "Module Access"),
    ("actions", "Action Access"),
    ("scope", "Data Scope"),
    ("temporary", "Temporary Access"),
    ("requests", "Access Requests"),
    ("review", "Access Review"),
    ("history", "Access History"),
    ("audit", "Permission Audit"),
    ("policy", "Access Policy"),
    ("emergency", "Emergency Access"),
    ("blocked", "Blocked / Restricted"),
    ("settings", "Access Settings"),
]


MEMBER_REQUIRED_SECTIONS = {
    "users", "matrix", "pages", "modules", "actions", "scope",
    "temporary", "requests", "review", "emergency", "blocked"
}

SECTION_COLLECTION = {
    "roles": "access_roles",
    "permissions": "access_permissions",
    "matrix": "access_role_permissions",
    "users": "access_user_access",
    "pages": "access_page_access",
    "modules": "access_module_access",
    "actions": "access_action_access",
    "scope": "access_data_scopes",
    "temporary": "access_temporary",
    "requests": "access_requests",
    "review": "access_reviews",
    "history": "access_history",
    "audit": "access_permission_audit",
    "policy": "access_policies",
    "emergency": "access_emergency",
    "blocked": "access_blocked",
    "settings": "access_settings",
}

DEFAULT_ROLES = [
    {"code": "SYSTEM_SUPER_ADMINISTRATOR", "name": "System Super Administrator", "level": 100, "scope": "GLOBAL", "parent": "", "status": "ACTIVE"},
    {"code": "CENTRAL_SYSTEM_ADMINISTRATOR", "name": "Central System Administrator", "level": 90, "scope": "CENTRAL", "parent": "SYSTEM_SUPER_ADMINISTRATOR", "status": "ACTIVE"},
    {"code": "BRANCH_OFFICER", "name": "Branch Officer", "level": 70, "scope": "BRANCH", "parent": "CENTRAL_SYSTEM_ADMINISTRATOR", "status": "ACTIVE"},
    {"code": "OPERATOR", "name": "Operator", "level": 40, "scope": "DEPARTMENT", "parent": "BRANCH_OFFICER", "status": "ACTIVE"},
    {"code": "MEMBER", "name": "Member", "level": 10, "scope": "OWN", "parent": "OPERATOR", "status": "ACTIVE"},
]

DEFAULT_PERMISSIONS = []
for _module in [
    "Home", "Income Management", "Expense Management", "Meal Management", "Savings Management",
    "Information Directory", "Blood Donor Management", "System Overview", "Branch Management",
    "Department Management", "Member Management", "Reports", "Access Management"
]:
    for _action in ["View", "Create", "Update", "Delete", "Approve", "Reject", "Export", "Import", "Manage"]:
        DEFAULT_PERMISSIONS.append({
            "code": f"{_module.upper().replace(' ', '_')}.{_action.upper()}",
            "name": f"{_module} — {_action}", "module": _module, "action": _action, "status": "ACTIVE"
        })


def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")


def _now():
    return datetime.now(timezone.utc)


def _oid(value):
    value = str(value or "")
    return ObjectId(value) if ObjectId.is_valid(value) else value


def _collection(section):
    name = SECTION_COLLECTION.get(section)
    if not name:
        raise ValueError("Unknown access-management section.")
    return get_database()[name]


def seed_defaults(context):
    _guard(context)
    db = get_database()
    for item in DEFAULT_ROLES:
        db["access_roles"].update_one({"code": item["code"]}, {"$setOnInsert": {**item, "created_at": _now(), "created_by": context.get("user_id")}}, upsert=True)
    for item in DEFAULT_PERMISSIONS:
        db["access_permissions"].update_one({"code": item["code"]}, {"$setOnInsert": {**item, "created_at": _now(), "created_by": context.get("user_id")}}, upsert=True)


def dashboard(context):
    _guard(context); seed_defaults(context); db = get_database()
    counts = {key: db[col].count_documents({}) for key, col in SECTION_COLLECTION.items()}
    active_roles = db["access_roles"].count_documents({"status": "ACTIVE"})
    active_permissions = db["access_permissions"].count_documents({"status": "ACTIVE"})
    pending_requests = db["access_requests"].count_documents({"status": "PENDING"})
    temporary = db["access_temporary"].count_documents({"status": "ACTIVE"})
    blocked = db["access_blocked"].count_documents({"status": "BLOCKED"})
    return {"counts": counts, "active_roles": active_roles, "active_permissions": active_permissions, "pending_requests": pending_requests, "temporary": temporary, "blocked": blocked}


def list_records(context, section, filters=None, limit=500):
    _guard(context); seed_defaults(context); filters = filters or {}; col = _collection(section); query = {}
    search = str(filters.get("search") or "").strip()
    status = str(filters.get("status") or "").strip()
    if search:
        fields = ["name", "code", "role", "role_code", "permission", "permission_code", "username", "user_id", "module", "page", "action", "scope", "branch", "department", "reason", "note", "requester", "policy_key"]
        query["$or"] = [{f: {"$regex": search, "$options": "i"}} for f in fields]
    if status:
        query["status"] = status
    return [clean(x) for x in col.find(query).sort("_id", -1).limit(int(limit))]


def role_options(context):
    """Return a reliable Role Name dropdown source.

    Built-in roles are always returned first so the UI never becomes empty
    when access_roles contains only partial/legacy records. Database records
    with the same role code override the built-in metadata.
    """
    _guard(context)
    seed_defaults(context)
    db = get_database()
    merged = {str(item["code"]): dict(item) for item in DEFAULT_ROLES}
    try:
        cursor = db["access_roles"].find({})
        for row in cursor:
            item = clean(row)
            code = str(item.get("code") or "").strip()
            if code:
                merged[code] = item
    except Exception:
        # Built-in roles remain usable even if an older database record
        # cannot be read/cleaned.
        pass

    result = []
    for code, item in merged.items():
        result.append({
            "_id": str(item.get("_id") or ""),
            "code": code,
            "name": str(item.get("name") or code.replace("_", " ").title()),
            "level": int(item.get("level") or 0),
            "scope": str(item.get("scope") or "OWN"),
            "parent": str(item.get("parent") or ""),
            "status": str(item.get("status") or "ACTIVE"),
        })
    result.sort(key=lambda x: (-x["level"], x["name"].lower()))
    return result


def users(context):
    """Return only currently active/unblocked users for access assignment.

    Different project modules may store the status value in slightly different
    forms, so the selector accepts the common ACTIVE variants while excluding
    explicitly locked users. Missing status is treated as ACTIVE for backward
    compatibility with older user records.
    """
    _guard(context); db = get_database()
    rows = []
    query = {
        "$and": [
            {"$or": [
                {"status": {"$exists": False}},
                {"status": None},
                {"status": "ACTIVE"},
                {"status": "Active"},
                {"status": "active"},
            ]},
            {"locked": {"$ne": True}},
        ]
    }
    for x in db["users"].find(query).sort("_id", 1).limit(1000):
        rows.append(clean({
            "id": str(x.get("_id", "")),
            "username": x.get("username") or x.get("name") or x.get("full_name") or "",
            "name": x.get("full_name") or x.get("name") or x.get("username") or "",
            "role": x.get("role") or "",
            "branch": x.get("branch_name") or x.get("branch") or "",
            "department": x.get("department_name") or x.get("department") or "",
            "status": x.get("status") or "ACTIVE",
        }))
    return rows


def _write_history(context, action, section, record_id="", before=None, after=None):
    db = get_database()
    db["access_history"].insert_one({
        "actor_id": context.get("user_id"), "actor_username": context.get("username"), "actor_role": ROLE,
        "action": action, "section": section, "record_id": str(record_id or ""),
        "before": before or {}, "after": after or {}, "created_at": _now()
    })


def create_record(context, section, data):
    _guard(context); seed_defaults(context); data = dict(data or {}); col = _collection(section)
    clean_data = {k: str(v).strip() for k, v in data.items() if k not in {"action", "record_id", "csrf_token"} and str(v).strip() != ""}
    target_user_id = clean_data.get("target_user_id", "")
    if section in MEMBER_REQUIRED_SECTIONS and not target_user_id:
        raise ValueError("Please select an active member before saving this access setting.")
    if target_user_id:
        target = get_database()["users"].find_one({"_id": _oid(target_user_id), "locked": {"$ne": True}})
        if not target:
            raise ValueError("Selected member is no longer active or could not be found.")
        status = str(target.get("status") or "ACTIVE").upper()
        if status not in {"ACTIVE", ""}:
            raise ValueError("Please select an active member. The selected account is not ACTIVE.")
        clean_data["target_user_id"] = target_user_id
        clean_data.setdefault("user_id", target_user_id)
        clean_data.setdefault("username", target.get("username") or target.get("name") or target.get("full_name") or "")
        clean_data.setdefault("role_code", target.get("role") or "")
        clean_data.setdefault("member_name", target.get("full_name") or target.get("name") or target.get("username") or "")
    clean_data.setdefault("status", "ACTIVE")
    clean_data.update({"created_at": _now(), "updated_at": _now(), "created_by": context.get("user_id"), "created_by_username": context.get("username")})
    if section == "roles":
        if not clean_data.get("code") or not clean_data.get("name"): raise ValueError("Role code and role name are required.")
        clean_data["level"] = int(clean_data.get("level") or 0)
        col.update_one({"code": clean_data["code"]}, {"$set": clean_data}, upsert=True)
        rid = col.find_one({"code": clean_data["code"]}).get("_id")
    elif section == "permissions":
        if not clean_data.get("code") or not clean_data.get("module") or not clean_data.get("action"): raise ValueError("Permission code, module and action are required.")
        col.update_one({"code": clean_data["code"]}, {"$set": clean_data}, upsert=True)
        rid = col.find_one({"code": clean_data["code"]}).get("_id")
    else:
        rid = col.insert_one(clean_data).inserted_id
    _write_history(context, "CREATE", section, rid, after=clean_data)
    if section in {"matrix", "pages", "modules", "actions"}:
        get_database()["access_permission_audit"].insert_one({"actor_id": context.get("user_id"), "actor_username": context.get("username"), "action": "PERMISSION_CHANGE", "section": section, "record_id": str(rid), "after": clean_data, "created_at": _now()})
    return str(rid)


def update_record(context, section, record_id, data):
    _guard(context); col = _collection(section); oid = _oid(record_id)
    old = col.find_one({"_id": oid})
    if not old: raise ValueError("Record not found.")
    item = {k: str(v).strip() for k, v in dict(data or {}).items() if k not in {"action", "record_id", "csrf_token"} and str(v).strip() != ""}
    if "level" in item:
        item["level"] = int(item["level"] or 0)
    item["updated_at"] = _now(); item["updated_by"] = context.get("user_id")
    col.update_one({"_id": oid}, {"$set": item})
    new = col.find_one({"_id": oid})
    _write_history(context, "UPDATE", section, record_id, before=clean(old), after=clean(new or {}))
    if section in {"matrix", "pages", "modules", "actions"}:
        get_database()["access_permission_audit"].insert_one({"actor_id": context.get("user_id"), "actor_username": context.get("username"), "action": "PERMISSION_CHANGE", "section": section, "record_id": str(record_id), "before": clean(old), "after": clean(new or {}), "created_at": _now()})
    return 1


def delete_record(context, section, record_id):
    _guard(context); col = _collection(section); oid = _oid(record_id); old = col.find_one({"_id": oid})
    if not old: raise ValueError("Record not found.")
    result = col.delete_one({"_id": oid})
    if result.deleted_count:
        _write_history(context, "DELETE", section, record_id, before=clean(old))
        if section in {"matrix", "pages", "modules", "actions"}:
            get_database()["access_permission_audit"].insert_one({"actor_id": context.get("user_id"), "actor_username": context.get("username"), "action": "PERMISSION_DELETE", "section": section, "record_id": str(record_id), "before": clean(old), "created_at": _now()})
    return result.deleted_count
