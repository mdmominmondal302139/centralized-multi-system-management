import os
from pathlib import Path
try:
    from pymongo import MongoClient
except ImportError:
    MongoClient = None
BASE_DIR=Path(__file__).resolve().parents[1]
def get_database_config():
    return {"uri":(os.getenv("MONGODB_URI") or "").strip(),"database_name":(os.getenv("DATABASE_NAME") or "ultimate_management_system").strip(),"timeout_ms":int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS") or "10000")}
def get_database():
    c=get_database_config()
    if not c["uri"]: raise RuntimeError("MONGODB_URI is not configured")
    if MongoClient is None: raise RuntimeError("PyMongo is not installed")
    return (client:=MongoClient(c["uri"],tls=True,serverSelectionTimeoutMS=c["timeout_ms"],connectTimeoutMS=c["timeout_ms"],socketTimeoutMS=c["timeout_ms"],retryWrites=True,retryReads=True)), client[c["database_name"]]
