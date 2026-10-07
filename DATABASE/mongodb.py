import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

_client = None

def get_database():
    global _client
    uri = (os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        raise RuntimeError("MONGODB_URI is not configured.")
    if _client is None:
        opts = {
            "serverSelectionTimeoutMS": int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "10000")),
            "connectTimeoutMS": int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "10000")),
            "retryWrites": True,
            "retryReads": True,
        }
        try:
            import certifi
            opts["tlsCAFile"] = certifi.where()
        except Exception:
            pass
        _client = MongoClient(uri, **opts)
    return _client[os.getenv("DATABASE_NAME", "development_my_expense_software")]

def clean(value):
    from bson import ObjectId
    from datetime import datetime
    if isinstance(value, ObjectId): return str(value)
    if isinstance(value, datetime): return value.isoformat()
    if isinstance(value, dict): return {k: clean(v) for k,v in value.items()}
    if isinstance(value, list): return [clean(v) for v in value]
    return value
