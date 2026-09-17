import shutil
from bson import BSON
from config.database import db

LIMIT_BYTES = 10 * 1024 * 1024
DATA_COLLECTIONS = ["incomes", "expenses", "meals", "savings"]

class StorageService:
    @staticmethod
    def _user(user_id):
        from config.database import users_collection
        try:
            from bson import ObjectId
            return users_collection.find_one({"_id": ObjectId(str(user_id))})
        except Exception:
            return users_collection.find_one({"_id": str(user_id)})

    @staticmethod
    def is_unlimited(user_id):
        user = StorageService._user(user_id)
        return bool(user and user.get("role") == "Expense Developer")

    @staticmethod
    def user_data_bytes(user_id):
        uid = str(user_id)
        total = 0
        for name in DATA_COLLECTIONS:
            for doc in db[name].find({"user_id": uid}):
                try:
                    total += len(BSON.encode(doc))
                except Exception:
                    total += len(str(doc).encode("utf-8"))
        return total

    @staticmethod
    def can_add(user_id, record):
        if StorageService.is_unlimited(user_id):
            return True, None
        current = StorageService.user_data_bytes(user_id)
        try:
            extra = len(BSON.encode(record))
        except Exception:
            extra = len(str(record).encode("utf-8"))
        if current + extra > LIMIT_BYTES:
            return False, "Your storage limit of 10 MB has been reached."
        return True, None

    @staticmethod
    def percent(user_id=None):
        usage = shutil.disk_usage("/")
        total = usage.total
        used = usage.used
        available = usage.free
        if total <= 0:
            return {"total": 0, "used": 0, "available": 0}
        return {
            "total": 100.0,
            "used": round(used * 100 / total, 2),
            "available": round(available * 100 / total, 2),
            "total_bytes": total,
            "used_bytes": used,
            "available_bytes": available,
        }
