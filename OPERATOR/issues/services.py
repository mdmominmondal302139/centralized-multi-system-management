"""OPERATOR registration service only."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
from pathlib import Path

from werkzeug.security import generate_password_hash

DATABASE_FILE = Path(__file__).resolve().parents[1] / "config" / "database.py"
spec = importlib.util.spec_from_file_location("operator_database_register", DATABASE_FILE)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Could not load database service: {DATABASE_FILE}")
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)

ROLE = "OPERATOR"
COLLECTION_NAME = "operators"


def _clean_username(value: str | None) -> str:
    return str(value or "").strip()


def _username_key(value: str) -> str:
    return value.casefold()


def register_user(data):
    """Create one persistent OPERATOR account."""
    name = str(data.get("name") or "").strip()
    username = _clean_username(data.get("username"))
    password = str(data.get("password") or "")
    email = str(data.get("email") or "").strip()

    if not name or not username or not password:
        return {"ok": False, "error": "Full Name, Username and Password are required."}
    if len(password) < 6:
        return {"ok": False, "error": "Password must be at least 6 characters."}

    client, db = database.get_mongo()
    try:
        collection = db[COLLECTION_NAME]
        username_key = _username_key(username)

        existing = collection.find_one({
            "$or": [{"username_key": username_key}, {"username": username}]
        })
        if existing:
            return {"ok": False, "error": "Username already exists."}

        if email and collection.find_one({"email": email}):
            return {"ok": False, "error": "Email already exists."}

        now = datetime.now(timezone.utc)
        document = {
            "name": name,
            "username": username,
            "username_key": username_key,
            "password_hash": generate_password_hash(password),
            "role": ROLE,
            "power": ROLE,
            "active": True,
            "created_at": now,
            "updated_at": now,
        }

        for key in ("mobile", "department", "branch_id", "section_id"):
            value = str(data.get(key) or "").strip()
            if value:
                document[key] = value

        result = collection.insert_one(document)
        return {"ok": True, "user_id": str(result.inserted_id)}
    except database.PyMongoError as exc:
        return {"ok": False, "error": f"Account could not be created: {exc}"}
    finally:
        client.close()
