"""Shared account collection and account lookup helpers."""
from DATABASE.mongodb import get_database

PREFERRED_COLLECTIONS = ("users", "members")

def get_db():
    return get_database()

def account_collection(db=None):
    if db is None:
        db = get_db()
    try:
        existing = set(db.list_collection_names())
    except Exception:
        existing = set()
    for name in PREFERRED_COLLECTIONS:
        if name in existing:
            return db[name]
    # The project login service already uses db["users"]. New installs keep that convention.
    return db["users"]

def find_active_account_by_email(email):
    email = (email or "").strip().lower()
    if not email:
        return None
    db = get_db()
    collections = []
    try:
        names = set(db.list_collection_names())
    except Exception:
        names = set()
    for name in PREFERRED_COLLECTIONS:
        if name in names:
            collections.append(db[name])
    if not collections:
        collections = [db["users"]]
    for coll in collections:
        row = coll.find_one({"email": {"$regex": "^" + __import__("re").escape(email) + "$", "$options": "i"}})
        if row and row.get("active") is not False and str(row.get("status") or "active").lower() not in {"inactive", "disabled", "blocked", "pending"}:
            row["_auth_collection"] = coll.name
            return row
    return None

def find_active_account_by_mobile(mobile):
    mobile = (mobile or "").strip()
    if not mobile:
        return None
    db = get_db()
    try:
        names = set(db.list_collection_names())
    except Exception:
        names = set()
    collections = [db[n] for n in PREFERRED_COLLECTIONS if n in names] or [db["users"]]
    for coll in collections:
        for field in ("mobile", "phone", "phone_number", "mobile_number"):
            row = coll.find_one({field: mobile})
            if row and row.get("active") is not False and str(row.get("status") or "active").lower() not in {"inactive", "disabled", "blocked", "pending"}:
                row["_auth_collection"] = coll.name
                return row
    return None
