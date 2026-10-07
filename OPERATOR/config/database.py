"""OPERATOR database compatibility adapter."""
from pathlib import Path
import importlib.util

BASE = Path(__file__).resolve().parent
_SPEC = importlib.util.spec_from_file_location("operator_database_base", BASE / "operator_database.py")
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Could not load operator_database.py")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
get_database_config = _MOD.get_database_config
get_mongo_client = _MOD.get_mongo_client
get_database = _MOD.get_database

try:
    from pymongo.errors import PyMongoError
except Exception:
    class PyMongoError(Exception):
        pass

def get_mongo():
    return get_database()
