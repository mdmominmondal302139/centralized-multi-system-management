# ROLE: OPERATOR
# OPERATOR database configuration

import os
from pathlib import Path

try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None

BASE_DIR = Path(__file__).resolve().parents[1]


def get_database_config():
    return {
        "uri": (os.getenv("MONGODB_URI") or "").strip(),
        "database_name": (os.getenv("DATABASE_NAME") or "ultimate_management_system").strip(),
        "timeout_ms": int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS") or "10000"),
    }


def get_mongo_client():
    config = get_database_config()
    if not config["uri"]:
        raise RuntimeError("MongoDB URI is not configured. Set MONGODB_URI in the project's .env file.")
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
    return MongoClient(config["uri"], **options)


def get_database():
    client = get_mongo_client()
    return client, client[get_database_config()["database_name"]]
