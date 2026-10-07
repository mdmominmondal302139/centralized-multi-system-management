import re
import hashlib
import base64
import hmac

from DATABASE.mongodb import get_database, clean


SYSTEM_ROLES = {
    "MEMBER",
    "BRANCH_OFFICER",
    "ACCOUNT_OFFICER",
    "MEAL_MANAGER",
    "OPERATOR",
    "SYSTEM_SUPER_ADMINISTRATOR",
    "BLOOD_DONOR",
}


def _normalize_role(value, fallback="MEMBER"):
    value = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "SYSTEM_SUPER_ADMIN": "SYSTEM_SUPER_ADMINISTRATOR",
        "SYSTEM_SUPER_ADMINISTRATOR": "SYSTEM_SUPER_ADMINISTRATOR",
        "BRANCH_OFFICER": "BRANCH_OFFICER",
        "ACCOUNT_OFFICER": "ACCOUNT_OFFICER",
        "ACCOUNTS_OFFICER": "ACCOUNT_OFFICER",
        "MEAL_MANAGER": "MEAL_MANAGER",
        "OPERATOR": "OPERATOR",
        "MEMBER": "MEMBER",
        "BLOOD_DONOR": "BLOOD_DONOR",
    }
    return aliases.get(value, fallback)


def _legacy_pbkdf2_ok(stored, password):
    try:
        parts = str(stored).split("$", 2)
        if len(parts) != 3:
            return False

        header, salt, expected = parts
        header_parts = header.split(":")
        if len(header_parts) != 3:
            return False

        algorithm, iterations_text, method = header_parts
        if algorithm.lower() != "pbkdf2":
            return False

        iterations = int(iterations_text)
        derived = hashlib.pbkdf2_hmac(
            method,
            str(password).encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )

        expected = expected.strip()

        # Current reset format used by this project.
        actual_base64 = base64.b64encode(derived).decode("ascii")
        if hmac.compare_digest(actual_base64, expected):
            return True

        # Compatibility with hex-encoded legacy records.
        actual_hex = derived.hex()
        if hmac.compare_digest(actual_hex, expected):
            return True

        return False
    except Exception as exc:
        print(f"[PASSWORD VERIFY ERROR] PBKDF2: {type(exc).__name__}: {exc}")
        return False


def _password_ok(stored, password):
    if stored is None:
        return False

    stored = str(stored)
    password = str(password or "")

    if not stored or not password:
        return False

    if stored.startswith("pbkdf2:"):
        return _legacy_pbkdf2_ok(stored, password)

    if stored.startswith("scrypt:"):
        try:
            from werkzeug.security import check_password_hash
            return bool(check_password_hash(stored, password))
        except Exception as exc:
            print(f"[PASSWORD VERIFY ERROR] scrypt: {type(exc).__name__}: {exc}")
            return False

    if stored.startswith(("$2a$", "$2b$", "$2y$")):
        try:
            import bcrypt
            return bool(bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8")))
        except Exception as exc:
            print(f"[PASSWORD VERIFY ERROR] bcrypt: {type(exc).__name__}: {exc}")
            return False

    return hmac.compare_digest(stored, password)


def _find_user(collection, username):
    value = str(username or "").strip()
    if not value:
        return None

    for field in ("username", "user_name", "login_username", "login", "user"):
        row = collection.find_one({field: value})
        if row:
            return row

    pattern = re.compile("^" + re.escape(value) + "$", re.IGNORECASE)
    for field in ("username", "user_name", "login_username", "login", "user"):
        row = collection.find_one({field: pattern})
        if row:
            return row

    return None


def _stored_password(row):
    for key in (
        "password_hash",
        "hashed_password",
        "passwordHash",
        "password",
        "passwd",
        "passcode",
        "pwd",
        "pass",
    ):
        value = row.get(key)
        if value is not None and str(value) != "":
            return value
    return None


def authenticate(username, password, role=""):
    db = get_database()
    username = str(username or "").strip()
    requested_role = _normalize_role(role, "") if str(role or "").strip() else ""

    if requested_role not in SYSTEM_ROLES:
        requested_role = ""

    if not username or not str(password or ""):
        return None

    # SYSTEM SUPER ADMINISTRATOR
    if not requested_role or requested_role == "SYSTEM_SUPER_ADMINISTRATOR":
        row = _find_user(db["system_super_administrators"], username)
        if (
            row
            and row.get("active", True) is not False
            and _password_ok(_stored_password(row), password)
        ):
            item = clean(row)
            item["role"] = "SYSTEM_SUPER_ADMINISTRATOR"
            item["username"] = item.get("username") or item.get("user_name") or username
            return item

    # NORMAL USERS
    row = _find_user(db["users"], username)
    if (
        row
        and row.get("active", True) is not False
        and _password_ok(_stored_password(row), password)
    ):
        item = clean(row)
        stored_role = _normalize_role(
            item.get("role") or item.get("power") or item.get("user_role"),
            "MEMBER",
        )
        if requested_role and requested_role != stored_role:
            return None
        item["role"] = stored_role
        item["username"] = item.get("username") or item.get("user_name") or username
        return item

    # BLOOD DONOR
    if not requested_role or requested_role == "BLOOD_DONOR":
        row = _find_user(
            db["system_super_administrator_blood_donor_accounts"],
            username,
        )
        if (
            row
            and str(row.get("status") or "ACTIVE").upper() == "ACTIVE"
            and _password_ok(_stored_password(row), password)
        ):
            item = clean(row)
            item["role"] = "BLOOD_DONOR"
            item["username"] = item.get("username") or item.get("user_name") or username
            item["name"] = item.get("full_name") or item.get("name") or username
            item["user_id"] = item.get("user_id") or item.get("account_user_id") or ""
            return item

    return None
