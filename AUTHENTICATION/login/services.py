import re
import hashlib
import base64
import hmac

from DATABASE.mongodb import get_database, clean, ensure_system_administrator_id


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
        if iterations <= 0:
            return False

        derived = hashlib.pbkdf2_hmac(
            method,
            str(password).encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )

        expected = expected.strip()
        actual_base64 = base64.b64encode(derived).decode("ascii")
        if hmac.compare_digest(actual_base64, expected):
            return True

        return hmac.compare_digest(derived.hex(), expected)
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

    # Backward compatibility for accounts whose password is stored as plain text.
    return hmac.compare_digest(stored, password)


def _find_user(collection, username):
    value = str(username or "").strip()
    if not value:
        return None

    fields = ("username", "user_name", "login_username", "login", "user")
    for field in fields:
        row = collection.find_one({field: value})
        if row:
            return row

    pattern = re.compile("^" + re.escape(value) + "$", re.IGNORECASE)
    for field in fields:
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


def _account_is_active(row):
    """Accept the project's existing active/status fields without treating
    a normal 'status: active' account as inactive."""
    if row.get("active") is False:
        return False
    status = str(row.get("status") or "").strip().lower()
    if status and status not in {"active", "enabled", "approved"}:
        return False
    return True


def _clean_account(row):
    """
    Normalize the returned account while preserving both identifiers:
    MongoDB _id is used for profile document lookup; user_id may be a separate
    UUID/business identifier and must not overwrite _id.
    """
    item = clean(row) or {}

    raw_id = row.get("_id")
    if raw_id is not None:
        item["_id"] = str(raw_id)

    if row.get("id") is not None:
        item["id"] = str(row.get("id"))

    if row.get("user_id") is not None:
        item["user_id"] = str(row.get("user_id"))

    if row.get("account_user_id") is not None:
        item["account_user_id"] = str(row.get("account_user_id"))

    return item


def authenticate(username, password, role=""):
    db = get_database()
    username = str(username or "").strip()
    password = str(password or "")

    requested_role = (
        _normalize_role(role, "")
        if str(role or "").strip()
        else ""
    )
    if requested_role not in SYSTEM_ROLES:
        requested_role = ""

    if not username or not password:
        return None

    # SYSTEM SUPER ADMINISTRATOR
    if not requested_role or requested_role == "SYSTEM_SUPER_ADMINISTRATOR":
        row = _find_user(db["system_super_administrators"], username)
        if row and _account_is_active(row) and _password_ok(_stored_password(row), password):
            # Allocate the persistent public ID (001, 002, ...) without
            # replacing MongoDB _id or the account's business user_id.
            try:
                row = ensure_system_administrator_id(row)
            except Exception as exc:
                # Do not prevent a valid login if ID assignment is temporarily
                # unavailable; the profile page will retry it.
                print(f"[ADMINISTRATOR ID ERROR] {type(exc).__name__}: {exc}")

            item = _clean_account(row)
            item["role"] = "SYSTEM_SUPER_ADMINISTRATOR"
            item["username"] = (
                item.get("username")
                or item.get("user_name")
                or item.get("login_username")
                or username
            )
            item["name"] = (
                item.get("name")
                or item.get("full_name")
                or item.get("fullName")
                or username
            )
            return item

    # NORMAL USERS
    row = _find_user(db["users"], username)
    if row and _account_is_active(row) and _password_ok(_stored_password(row), password):
        item = _clean_account(row)
        stored_role = _normalize_role(
            item.get("role") or item.get("power") or item.get("user_role"),
            "MEMBER",
        )
        if requested_role and requested_role != stored_role:
            return None
        item["role"] = stored_role
        item["username"] = (
            item.get("username")
            or item.get("user_name")
            or item.get("login_username")
            or username
        )
        item["name"] = (
            item.get("name")
            or item.get("full_name")
            or item.get("fullName")
            or username
        )
        return item

    # BLOOD DONOR
    if not requested_role or requested_role == "BLOOD_DONOR":
        row = _find_user(
            db["system_super_administrator_blood_donor_accounts"],
            username,
        )
        if (
            row
            and str(row.get("status") or "ACTIVE").strip().upper() == "ACTIVE"
            and _password_ok(_stored_password(row), password)
        ):
            item = _clean_account(row)
            item["role"] = "BLOOD_DONOR"
            item["username"] = (
                item.get("username")
                or item.get("user_name")
                or item.get("login_username")
                or username
            )
            item["name"] = item.get("full_name") or item.get("name") or username
            return item

    return None
