"""Database access for the Blood Donor Management module.

This file owns MongoDB connection details for this module only.
No route, HTML, or service code is stored here.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None

BASE_DIR = Path(__file__).resolve().parents[2]

_client = None
_database = None


def get_database_config() -> dict[str, Any]:
    return {
        "uri": (os.getenv("MONGODB_URI") or "").strip(),
        "database_name": (
            os.getenv("DATABASE_NAME") or "ultimate_management_system"
        ).strip(),
        "timeout_ms": int(
            os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS") or "10000"
        ),
    }


def get_database():
    """Return (client, database), creating the connection lazily."""
    global _client, _database

    if _database is not None:
        return _client, _database

    config = get_database_config()

    if not config["uri"]:
        raise RuntimeError(
            "MONGODB_URI is not configured. Set MONGODB_URI before using Blood Donor Management."
        )

    if MongoClient is None:
        raise RuntimeError("PyMongo is not installed.")

    timeout = config["timeout_ms"]
    options = {
        "tls": True,
        "serverSelectionTimeoutMS": timeout,
        "connectTimeoutMS": timeout,
        "socketTimeoutMS": timeout,
        "retryWrites": True,
        "retryReads": True,
    }

    try:
        import certifi
        options["tlsCAFile"] = certifi.where()
    except ImportError:
        pass

    _client = MongoClient(config["uri"], **options)
    _database = _client[config["database_name"]]
    return _client, _database


def close_database() -> None:
    global _client, _database
    if _client is not None:
        _client.close()
    _client = None
    _database = None
