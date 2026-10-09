from datetime import datetime, timezone
import re
from pymongo import ASCENDING, ReturnDocument

from bson import ObjectId
from DATABASE.mongodb import get_database, clean

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
COLLECTION = "users"


def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")


def _text(value):
    return str(value or "").strip()


def _normal(value):
    return _text(value).casefold()


def _branch_value(document):
    """Return the first usable branch label stored on a user record."""
    for key in ("branch_name", "branch", "branchName", "branch_label"):
        value = document.get(key)
        if value is not None and _text(value):
            return _text(value)
    return ""



def _created_sort_key(doc):
    """Stable creation order for legacy accounts; ObjectId embeds creation time."""
    for key in ("created_at", "created_on", "registered_at", "createdAt", "date_created"):
        value = doc.get(key)
        if isinstance(value, datetime):
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
            except ValueError:
                pass
    oid = doc.get("_id")
    if isinstance(oid, ObjectId):
        return oid.generation_time
    return datetime.max.replace(tzinfo=timezone.utc)


def _member_role(doc):
    return _normal(doc.get("role")) == "member"


def ensure_member_ids(context):
    """Backfill missing MEMBER IDs in account-creation order and enforce uniqueness."""
    _guard(context)
    db = get_database()
    users = db[COLLECTION]
    members = list(users.find({"role": {"$regex": "^MEMBER$", "$options": "i"}}))
    if not members:
        return
    members.sort(key=lambda doc: (_created_sort_key(doc), str(doc.get("_id", ""))))

    # Existing IDs are preserved. Numeric IDs determine the next available sequence.
    used = set()
    max_number = 0
    for doc in members:
        value = _text(doc.get("member_id"))
        if value:
            used.add(value.casefold())
            if value.isdigit():
                max_number = max(max_number, int(value))

    # Preserve legacy values, but repair duplicates among MEMBER accounts deterministically.
    seen = set()
    for doc in members:
        original_value = _text(doc.get("member_id"))
        duplicate_value = bool(original_value and original_value.casefold() in seen)
        if original_value and not duplicate_value:
            seen.add(original_value.casefold())
            continue
        while True:
            max_number += 1
            candidate = f"{max_number:03d}"
            if candidate.casefold() not in used and candidate.casefold() not in seen:
                break
        if duplicate_value:
            query = {"_id": doc["_id"], "member_id": original_value}
        else:
            query = {"_id": doc["_id"], "$or": [{"member_id": {"$exists": False}}, {"member_id": None}, {"member_id": ""}]}
        result = users.update_one(
            query,
            {"$set": {"member_id": candidate, "member_id_mode": "automatic",
                      "member_id_assigned_at": datetime.now(timezone.utc)}},
        )
        if result.modified_count:
            used.add(candidate.casefold())
            seen.add(candidate.casefold())

    # A unique sparse index protects future manual/automatic IDs.
    # Existing duplicate IDs are resolved above before index creation.
    users.create_index([("member_id", ASCENDING)], unique=True, sparse=True,
                       name="unique_member_id")


def _next_member_id(users):
    """Allocate the next three-digit serial atomically through a MongoDB counter."""
    counter = get_database()["system_counters"]
    # Keep counter at least as high as all numeric IDs already present.
    max_existing = 0
    for doc in users.find({"member_id": {"$type": "string"}}, {"member_id": 1}):
        value = _text(doc.get("member_id"))
        if value.isdigit():
            max_existing = max(max_existing, int(value))
    counter.update_one({"_id": "member_id_sequence"},
                       {"$max": {"value": max_existing}}, upsert=True)
    while True:
        current = counter.find_one_and_update(
            {"_id": "member_id_sequence"},
            {"$inc": {"value": 1}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
        candidate = f"{int(current.get('value', 1)):03d}"
        if not users.find_one({"member_id": candidate}, {"_id": 1}):
            return candidate


def _validate_member_id(users, record_id, data):
    mode = _text(data.get("member_id_mode", "automatic")).lower()
    if mode not in ("automatic", "manual"):
        raise ValueError("Please select Automatic or Admin Manual Member ID mode.")
    current = users.find_one({"_id": record_id}, {"member_id": 1, "role": 1})
    if not current:
        raise ValueError("The selected account was not found.")
    is_member = _member_role(current)
    if not is_member:
        return {}
    if mode == "automatic":
        value = _text(current.get("member_id"))
        if not value:
            value = _next_member_id(users)
        return {"member_id": value, "member_id_mode": "automatic"}
    value = _text(data.get("member_id"))
    if not value:
        raise ValueError("Admin Manual mode requires a Member ID.")
    duplicate = users.find_one({"member_id": value, "_id": {"$ne": record_id}}, {"_id": 1})
    if duplicate:
        raise ValueError(f"Member ID '{value}' is already assigned to another account.")
    return {"member_id": value, "member_id_mode": "manual"}


def list_branches(context):
    _guard(context)
    db = get_database()
    names = set()
    for collection_name in ("branches", "branch_management"):
        if collection_name not in db.list_collection_names():
            continue
        for branch in db[collection_name].find({}):
            name = _text(branch.get("branch_name") or branch.get("name") or branch.get("branch"))
            if name:
                names.add(name)
    # Include branch labels already used on accounts, so legacy account records
    # remain filterable even if the branch collection uses a different schema.
    for user in db[COLLECTION].find({}, {"branch": 1, "branch_name": 1, "branchName": 1, "branch_label": 1}):
        name = _branch_value(user)
        if name:
            names.add(name)
    return sorted(names, key=str.casefold)


def list_records(context, filters=None):
    _guard(context)
    filters = filters or {}
    selected_branch = _text(filters.get("branch"))
    term = _text(filters.get("search"))
    selected_role = _text(filters.get("role"))
    selected_status = _text(filters.get("status"))

    # The page intentionally requires a branch selection before listing records.
    if not selected_branch:
        return []

    db = get_database()
    query = {}
    if selected_role:
        query["role"] = {"$regex": "^" + re.escape(selected_role) + "$", "$options": "i"}
    if selected_status:
        query["status"] = {"$regex": "^" + re.escape(selected_status) + "$", "$options": "i"}
    if term:
        rx = {"$regex": re.escape(term), "$options": "i"}
        query["$or"] = [
            {"full_name": rx}, {"name": rx}, {"username": rx}, {"email": rx},
            {"phone": rx}, {"role": rx}, {"branch": rx}, {"branch_name": rx},
            {"department": rx}, {"department_name": rx},
        ]

    # Use branch aliases supported by the existing application. Branch IDs are
    # resolved through the branch collections where possible.
    branch_query_values = {selected_branch}
    branch_id_values = set()
    for collection_name in ("branches", "branch_management"):
        if collection_name not in db.list_collection_names():
            continue
        for b in db[collection_name].find({}):
            name = _text(b.get("branch_name") or b.get("name") or b.get("branch"))
            if _normal(name) == _normal(selected_branch):
                if b.get("_id") is not None:
                    branch_id_values.add(str(b["_id"]))
                for key in ("branch_id", "id", "code", "branch_code"):
                    if b.get(key) is not None:
                        branch_id_values.add(str(b[key]))

    # Query broad aliases, then verify the actual branch label in Python to
    # support mixed legacy schemas without exposing records from another branch.
    branch_conditions = [
        {"branch": {"$in": list(branch_query_values)}},
        {"branch_name": {"$in": list(branch_query_values)}},
        {"branchName": {"$in": list(branch_query_values)}},
        {"branch_label": {"$in": list(branch_query_values)}},
    ]
    if branch_id_values:
        branch_conditions.extend([
            {"branch_id": {"$in": list(branch_id_values)}},
            {"branchId": {"$in": list(branch_id_values)}},
        ])
    # If the search $or exists, preserve it as an AND condition.
    base_query = {k: v for k, v in query.items() if k != "$or"}
    base_query["$or"] = branch_conditions
    if "$or" in query:
        base_query["$and"] = [{"$or": query["$or"]}]
    docs = list(db[COLLECTION].find(base_query).sort("_id", -1).limit(5000))

    # Resolve ID-only records by matching the selected branch's known IDs.
    # For name-based records, exact case-insensitive matching is enforced here.
    results = []
    for doc in docs:
        label = _branch_value(doc)
        if label:
            if _normal(label) != _normal(selected_branch):
                continue
        else:
            ref = _text(doc.get("branch_id") or doc.get("branchId"))
            if not ref or ref not in branch_id_values:
                continue
        results.append(clean(doc))
    return results


def get_record(context, record_id):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(_text(record_id)) else record_id
    doc = get_database()[COLLECTION].find_one({"_id": oid})
    return clean(doc) if doc else None


def update_record(context, record_id, data):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(_text(record_id)) else record_id
    data = dict(data or {})
    users = get_database()[COLLECTION]
    allowed = ("full_name", "name", "email", "phone", "role", "status",
               "branch", "branch_name", "branchName", "department", "department_name",
               "blood_group", "present_address", "permanent_address", "approval_status",
               "account_locked")
    updates = {}
    for key in allowed:
        if key in data:
            value = _text(data.get(key))
            if key == "email":
                value = value.lower()
            if key == "account_locked":
                value = value.lower() in ("1", "true", "yes", "locked", "on")
            updates[key] = value
    # Member ID is editable only for MEMBER accounts. Automatic mode is server-controlled.
    current = users.find_one({"_id": oid})
    if not current:
        raise ValueError("The selected account was not found.")
    if _member_role(current):
        updates.update(_validate_member_id(users, oid, data))
    if not updates:
        raise ValueError("No editable fields were provided.")
    updates["updated_at"] = datetime.now(timezone.utc)
    try:
        result = users.update_one({"_id": oid}, {"$set": updates})
    except Exception as exc:
        if "duplicate key" in str(exc).lower() or getattr(exc, "code", None) == 11000:
            raise ValueError("This Member ID is already in use. Please enter a unique ID.") from exc
        raise
    if not result.matched_count:
        raise ValueError("The selected account was not found.")
    return result.modified_count or result.matched_count


def deactivate_record(context, record_id):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(_text(record_id)) else record_id
    result = get_database()[COLLECTION].update_one(
        {"_id": oid},
        {"$set": {"status": "Inactive", "updated_at": datetime.now(timezone.utc)}},
    )
    if not result.matched_count:
        raise ValueError("The selected account was not found.")
    return result.modified_count or result.matched_count


def activate_record(context, record_id):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(_text(record_id)) else record_id
    result = get_database()[COLLECTION].update_one(
        {"_id": oid},
        {"$set": {"status": "Active", "updated_at": datetime.now(timezone.utc)}},
    )
    if not result.matched_count:
        raise ValueError("The selected account was not found.")
    return result.modified_count or result.matched_count


def delete_record(context, record_id):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(_text(record_id)) else record_id
    result = get_database()[COLLECTION].delete_one({"_id": oid})
    if not result.deleted_count:
        raise ValueError("The selected account was not found.")
    return result.deleted_count
