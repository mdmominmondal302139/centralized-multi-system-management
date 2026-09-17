from datetime import datetime
from config.database import db
from bson import ObjectId

requests_collection = db["member_requests"]

class RequestService:
    @staticmethod
    def create(user, request_type, details=""):
        requests_collection.insert_one({
            "user_id": str(user.get("_id")),
            "name": user.get("name", ""),
            "mobile": user.get("mobile", ""),
            "role": user.get("role", "Member"),
            "request_type": request_type,
            "details": details,
            "created_at": datetime.now(),
        })

    @staticmethod
    def get_all():
        return list(requests_collection.find().sort("_id", -1))

    @staticmethod
    def delete(request_id):
        try:
            result = requests_collection.delete_one({"_id": ObjectId(request_id)})
            return result.deleted_count == 1
        except Exception:
            return False
