from datetime import datetime, timezone
from bson import ObjectId
from werkzeug.security import check_password_hash, generate_password_hash
from DATABASE.mongodb import get_database, clean, ensure_system_administrator_id

ROLE = "SYSTEM_SUPER_ADMINISTRATOR"
COLLECTION = "profile"
USERS_COLLECTION = "users"


def _guard(context):
    if not isinstance(context, dict) or context.get("role") != ROLE:
        raise PermissionError("Access denied.")


def _user_filter(user_id):
    value = str(user_id or "").strip()
    if not value:
        raise PermissionError("User session is invalid.")
    if ObjectId.is_valid(value):
        return {"_id": ObjectId(value)}
    return {"_id": value}


def _find_current_user_with_collection(context):
    """Find the signed-in account in the collection used by the login service.

    SYSTEM_SUPER_ADMINISTRATOR accounts authenticate against
    ``system_super_administrators`` (not ``users``). Other account roles use
    ``users``. Exact session IDs are preferred; then exact login identifiers.
    """
    db = get_database()
    role = str((context or {}).get("role") or "").strip().upper()

    if role == ROLE:
        collection_names = ("system_super_administrators", "users")
    else:
        collection_names = ("users", "system_super_administrators")

    id_values = []
    for key in ("user_id", "_id", "id"):
        value = str((context or {}).get(key) or "").strip()
        if value and value not in id_values:
            id_values.append(value)

    identifier_fields = (
        "username", "user_name", "login_username", "login", "user",
        "email", "phone", "administrator_id", "member_id", "login_id",
        "user_id", "account_user_id",
    )
    context_keys = (
        "username", "email", "phone", "administrator_id", "member_id",
        "login_id", "user_id", "id", "_id",
    )

    for collection_name in collection_names:
        collection = db[collection_name]

        for value in id_values:
            if ObjectId.is_valid(value):
                try:
                    user = collection.find_one({"_id": ObjectId(value)})
                    if user:
                        return collection_name, user
                except Exception:
                    pass
            try:
                user = collection.find_one({"_id": value})
                if user:
                    return collection_name, user
            except Exception:
                pass

        seen = set()
        for context_key in context_keys:
            value = str((context or {}).get(context_key) or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            for field in identifier_fields:
                try:
                    user = collection.find_one({field: value})
                    if user:
                        return collection_name, user
                except Exception:
                    continue

    return None, None


def _find_current_user(context):
    """Compatibility wrapper returning only the matched MongoDB document."""
    _collection_name, user = _find_current_user_with_collection(context)
    return user


def _selector_for_user(user, context):
    """Return a selector for the actual matched MongoDB account."""
    if user and user.get("_id") is not None:
        return {"_id": user["_id"]}
    user_id = str(context.get("user_id") or "").strip()
    if user_id:
        return _user_filter(user_id)
    username = str(context.get("username") or "").strip()
    if username:
        return {"username": username}
    raise PermissionError("User session is invalid.")


def get_current_profile(context):
    _guard(context)
    collection_name, user = _find_current_user_with_collection(context)

    if user:
        # Ensure every signed-in administrator has a persistent public ID.
        # This is separate from MongoDB _id and user_id.
        if collection_name == "system_super_administrators":
            user = ensure_system_administrator_id(user)
        result = clean(user)
    else:
        # Fallback to the session so the page remains usable with older user records.
        result = {
            "name": context.get("username", ""),
            "username": context.get("username", ""),
            "email": "",
            "phone": "",
            "role": ROLE,
            "branch_name": context.get("branch_name", ""),
        }

    result.setdefault("role", ROLE)
    result.setdefault("username", context.get("username", ""))
    result.setdefault("branch_name", context.get("branch_name", ""))
    result.setdefault("status", result.get("account_status", "ACTIVE"))

    # Normalize metadata from common legacy field names used by existing user records.
    created = next((result.get(k) for k in ("created_at", "created_date", "date_created", "registered_at", "joined_at") if result.get(k)), None)
    if not created and result.get("_id") is not None and hasattr(result.get("_id"), "generation_time"):
        created = result["_id"].generation_time
    result["created_at"] = _display_datetime(created) if created else "Not recorded in MongoDB"

    updated = next((result.get(k) for k in ("updated_at", "last_updated", "modified_at", "updated_on") if result.get(k)), None)
    result["updated_at"] = _display_datetime(updated) if updated else "Not recorded in MongoDB"

    pwd_changed = next((result.get(k) for k in ("last_password_change", "password_changed_at", "password_updated_at", "last_password_change_at") if result.get(k)), None)
    result["last_password_change"] = _display_datetime(pwd_changed) if pwd_changed else "Not recorded in MongoDB"

    two_factor = next((result.get(k) for k in ("two_factor_enabled", "two_factor", "mfa_enabled", "is_2fa_enabled") if k in result), None)
    result["two_factor_enabled"] = bool(two_factor) if two_factor is not None else None

    failed = next((result.get(k) for k in ("failed_login_attempts", "failed_attempts", "login_attempts_failed", "login_failures") if k in result), None)
    result["failed_login_attempts"] = failed if failed is not None else "Not tracked in MongoDB"

    locked = next((result.get(k) for k in ("account_locked", "locked", "is_locked", "lockout") if k in result), None)
    result["account_locked"] = bool(locked) if locked is not None else None
    result["account_lock_status"] = ("Locked" if locked else "Not locked") if locked is not None else "Not tracked in MongoDB"
    return result


def _display_datetime(value):
    if isinstance(value, datetime):
        try:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        except Exception:
            return value.isoformat()
    return str(value)


def update_profile(context, data):
    _guard(context)
    db = get_database()
    allowed = (
        "name", "username", "email", "phone", "address",
        "designation", "department", "branch_name",
        "father_name", "mother_name"
    )
    item = {}
    for key in allowed:
        if key in data:
            item[key] = str(data.get(key, "")).strip()

    if not item.get("username"):
        raise ValueError("Username is required.")
    if not item.get("email"):
        raise ValueError("Email address is required.")

    # Do not allow a user to modify protected authority/security fields.
    item.pop("role", None)
    item.pop("status", None)
    item.pop("approved", None)
    item.pop("locked", None)
    item.pop("password", None)

    item["updated_at"] = datetime.now(timezone.utc)
    collection_name, user = _find_current_user_with_collection(context)
    if not user:
        raise ValueError(
            "Profile account was not found in the login account collection. "
            "The signed-in user ID/username does not match a saved account."
        )
    result = db[collection_name].update_one(_selector_for_user(user, context), {"$set": item})
    if not result.matched_count:
        raise ValueError("Profile account was found but could not be updated.")

    return get_current_profile(context)


def change_password(context, current_password, new_password, confirm_password):
    _guard(context)
    current_password = str(current_password or "")
    new_password = str(new_password or "")
    confirm_password = str(confirm_password or "")

    if not current_password or not new_password or not confirm_password:
        raise ValueError("All password fields are required.")
    if new_password != confirm_password:
        raise ValueError("New password and confirmation do not match.")
    if len(new_password) < 8:
        raise ValueError("New password must contain at least 8 characters.")

    db = get_database()
    collection_name, user = _find_current_user_with_collection(context)
    if not user:
        raise ValueError(
            "Profile account was not found in the login account collection. "
            "The signed-in user ID/username does not match a saved account."
        )

    stored = str(user.get("password") or user.get("password_hash") or "")
    valid = False
    if stored:
        try:
            valid = check_password_hash(stored, current_password)
        except Exception:
            valid = stored == current_password

    if not valid:
        raise ValueError("Current password is incorrect.")

    hashed = generate_password_hash(new_password)
    field = "password_hash" if user.get("password_hash") is not None else "password"
    db[collection_name].update_one(
        _selector_for_user(user, context),
        {"$set": {field: hashed, "updated_at": datetime.now(timezone.utc), "last_password_change": datetime.now(timezone.utc)}}
    )


def list_records(context, filters=None):
    _guard(context)
    filters = filters or {}
    db = get_database()
    query = {}
    for key in ("search", "date", "month", "member", "branch", "status"):
        value = str(filters.get(key) or "").strip()
        if not value:
            continue
        if key == "search":
            query["$or"] = [
                {k: {"$regex": value, "$options": "i"}}
                for k in (
                    "name", "username", "email", "phone", "note", "source",
                    "member_name", "branch_name", "type", "status"
                )
            ]
        elif key == "month":
            query["date"] = {"$regex": f"^{value}"}
        elif key == "member":
            query["$or"] = [
                {"member_name": {"$regex": value, "$options": "i"}},
                {"member_id": {"$regex": value, "$options": "i"}},
            ]
        elif key == "branch":
            query["branch_name"] = {"$regex": value, "$options": "i"}
        else:
            query[key] = value
    return [clean(x) for x in db[COLLECTION].find(query).sort("_id", -1).limit(500)]


def create_record(context, data):
    _guard(context)
    item = dict(data or {})
    item.update({
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "created_by": context.get("user_id"),
        "created_by_role": ROLE,
    })
    r = get_database()[COLLECTION].insert_one(item)
    return str(r.inserted_id)


def update_record(context, record_id, data):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    item = dict(data or {})
    item.pop("_id", None)
    item.pop("action", None)
    item["updated_at"] = datetime.now(timezone.utc)
    r = get_database()[COLLECTION].update_one({"_id": oid}, {"$set": item})
    return r.modified_count or r.matched_count


def delete_record(context, record_id):
    _guard(context)
    oid = ObjectId(record_id) if ObjectId.is_valid(str(record_id)) else record_id
    r = get_database()[COLLECTION].delete_one({"_id": oid})
    return r.deleted_count
