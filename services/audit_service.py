from datetime import datetime

from config.database import db
from bson import ObjectId


audit_collection = db["audit_logs"]


class AuditService:

    @staticmethod
    def log(
        user_id=None,
        action="",
        description="",
        user=None
    ):
        """
        Save an activity log.
        """

        try:
            uid = None

            if user_id:
                uid = str(user_id)

            user_name = ""

            if user:
                user_name = str(
                    user.get("name", "")
                ).strip()

            data = {
                "user_id": uid,
                "user_name": user_name,
                "action": str(action or ""),
                "description": str(description or ""),
                "created_at": datetime.now()
            }

            audit_collection.insert_one(data)

            return True

        except Exception:
            return False

    @staticmethod
    def get_all():
        """
        Return all audit logs.
        """

        try:
            return list(
                audit_collection.find().sort(
                    "created_at",
                    -1
                )
            )
        except Exception:
            return []

    @staticmethod
    def get_user_logs(user_id):
        """
        Return audit logs for a specific user.
        """

        try:
            uid = str(user_id)

            return list(
                audit_collection.find(
                    {
                        "user_id": uid
                    }
                ).sort(
                    "created_at",
                    -1
                )
            )

        except Exception:
            return []

    @staticmethod
    def delete_log(log_id):
        """
        Delete one audit log.
        """

        try:
            result = audit_collection.delete_one(
                {
                    "_id": ObjectId(log_id)
                }
            )

            if result.deleted_count:
                return True, "Audit log deleted successfully."

            return False, "Audit log not found."

        except Exception:
            return False, "Invalid audit log ID."