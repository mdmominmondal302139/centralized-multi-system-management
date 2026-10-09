import os

from pymongo import MongoClient
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# GLOBAL MONGODB CLIENT
# =========================================================

_client = None


# =========================================================
# GET DATABASE
# =========================================================

def get_database():
    global _client

    uri = (os.getenv("MONGODB_URI") or "").strip()

    if not uri:
        raise RuntimeError(
            "MONGODB_URI is not configured."
        )

    database_name = (
        os.getenv(
            "DATABASE_NAME",
            "development_my_expense_software"
        ).strip()
    )

    timeout_ms = int(
        os.getenv(
            "MONGO_SERVER_SELECTION_TIMEOUT_MS",
            "10000"
        )
    )

    # -----------------------------------------------------
    # Create MongoDB client only once
    # -----------------------------------------------------

    if _client is None:

        options = {
            "serverSelectionTimeoutMS": timeout_ms,
            "connectTimeoutMS": timeout_ms,
            "socketTimeoutMS": timeout_ms,

            "retryWrites": True,
            "retryReads": True,

            "tls": True,
        }

        # -------------------------------------------------
        # Use certifi CA certificate when available
        # -------------------------------------------------

        try:
            import certifi

            options["tlsCAFile"] = certifi.where()

        except Exception:
            pass

        # -------------------------------------------------
        # Create MongoDB client
        # -------------------------------------------------

        _client = MongoClient(
            uri,
            **options
        )

    # -----------------------------------------------------
    # Return selected database
    # -----------------------------------------------------

    return _client[database_name]


# =========================================================
# TEST DATABASE CONNECTION
# =========================================================

def check_database_connection():
    """
    Checks whether MongoDB is reachable.

    Returns:
        True  -> connection successful
        False -> connection failed
    """

    global _client

    uri = (os.getenv("MONGODB_URI") or "").strip()

    if not uri:
        return False

    database_name = (
        os.getenv(
            "DATABASE_NAME",
            "development_my_expense_software"
        ).strip()
    )

    timeout_ms = int(
        os.getenv(
            "MONGO_SERVER_SELECTION_TIMEOUT_MS",
            "10000"
        )
    )

    try:

        if _client is None:

            options = {
                "serverSelectionTimeoutMS": timeout_ms,
                "connectTimeoutMS": timeout_ms,
                "socketTimeoutMS": timeout_ms,

                "retryWrites": True,
                "retryReads": True,

                "tls": True,
            }

            try:
                import certifi

                options["tlsCAFile"] = certifi.where()

            except Exception:
                pass

            _client = MongoClient(
                uri,
                **options
            )

        # -------------------------------------------------
        # Force an actual connection test
        # -------------------------------------------------

        _client.admin.command("ping")

        # Make sure database reference is valid.
        _ = _client[database_name]

        return True

    except Exception:
        return False


# =========================================================
# CLEAN MONGODB VALUES
# =========================================================

def clean(value):

    from bson import ObjectId
    from datetime import datetime

    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {
            key: clean(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [
            clean(item)
            for item in value
        ]

    return value

# =========================================================
# SYSTEM SUPER ADMINISTRATOR ID (001, 002, 003, ...)
# =========================================================

def ensure_system_administrator_id(account):
    """
    Assign a persistent, sequential administrator ID to an existing
    system_super_administrators document if it does not have one yet.

    MongoDB _id and user_id remain unchanged. The public administrator ID
    is stored separately in administrator_id.
    """
    if not isinstance(account, dict) or account.get("_id") is None:
        return account

    current = str(account.get("administrator_id") or "").strip()
    if current:
        account["administrator_id"] = current
        return account

    db = get_database()
    administrators = db["system_super_administrators"]
    counters = db["system_counters"]
    counter_key = "system_super_administrator_id"

    # Seed the counter from existing numeric administrator IDs so an
    # existing ID is never intentionally reused.
    max_existing = 0
    try:
        for row in administrators.find(
            {"administrator_id": {"$exists": True, "$nin": [None, ""]}},
            {"administrator_id": 1},
        ):
            value = str(row.get("administrator_id") or "").strip()
            if value.isdigit():
                max_existing = max(max_existing, int(value))
    except Exception:
        pass

    counters.update_one(
        {"_id": counter_key},
        {"$max": {"seq": max_existing}},
        upsert=True,
    )

    from pymongo import ReturnDocument

    # Incrementing a single MongoDB counter document is atomic.
    counter = counters.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    seq = int(counter.get("seq", 1))
    generated = f"{seq:03d}"

    # Only assign if another request has not already assigned one.
    result = administrators.update_one(
        {
            "_id": account["_id"],
            "$or": [
                {"administrator_id": {"$exists": False}},
                {"administrator_id": None},
                {"administrator_id": ""},
            ],
        },
        {"$set": {"administrator_id": generated}},
    )

    saved = administrators.find_one({"_id": account["_id"]})
    if saved:
        # Preserve the original BSON _id type in the caller's document.
        # Converting it to a string here would break later MongoDB updates.
        account["administrator_id"] = saved.get("administrator_id", generated)
    else:
        account["administrator_id"] = generated

    return account
