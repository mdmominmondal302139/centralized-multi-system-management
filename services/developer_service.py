import re

from config.database import users_collection, db
from utils.password_utils import hash_password
from models.user import User
from bson import ObjectId


class DeveloperService:

    @staticmethod
    def _valid_username(username):
        """
        Username:
        - lowercase only
        - a-z
        - 0-9
        - underscore
        """

        if not username:
            return False

        return bool(
            re.fullmatch(
                r"[a-z0-9_]+",
                username
            )
        )

    @staticmethod
    def _valid_password(password):
        """
        Password must contain at least 8 characters.
        """

        return bool(password) and len(password) >= 8

    @staticmethod
    def create_member(
        name,
        username,
        mobile,
        email,
        password,
        role
    ):

        name = str(
            name or ""
        ).strip()

        username = str(
            username or ""
        ).strip()

        mobile = str(
            mobile or ""
        ).strip()

        email = str(
            email or ""
        ).strip()

        password = str(
            password or ""
        )

        # -----------------------------
        # Required fields
        # -----------------------------

        if not name:
            return False, "Name is required."

        if not username:
            return False, "Username is required."

        if not mobile:
            return False, "Mobile is required."

        if not email:
            return False, "Email is required."

        if not password:
            return False, "Password is required."

        # -----------------------------
        # Username validation
        # -----------------------------

        if username != username.lower():
            return (
                False,
                "Username must be lowercase."
            )

        if not DeveloperService._valid_username(
            username
        ):
            return (
                False,
                "Invalid username. Use lowercase letters, numbers and underscore only."
            )

        # -----------------------------
        # Password validation
        # -----------------------------

        if not DeveloperService._valid_password(
            password
        ):
            return (
                False,
                "Password must be at least 8 characters."
            )

        # -----------------------------
        # Role validation
        # -----------------------------

        if role not in [
            "Expense Developer",
            "Manager"
        ]:
            return (
                False,
                "Invalid role."
            )

        # -----------------------------
        # Duplicate checking
        # -----------------------------

        existing = users_collection.find_one(
            {
                "$or": [
                    {"email": email},
                    {"mobile": mobile},
                    {"name": name},
                    {"username": username}
                ]
            }
        )

        if existing:

            if existing.get(
                "username"
            ) == username:

                return (
                    False,
                    "Username already registered."
                )

            if existing.get(
                "email"
            ) == email:

                return (
                    False,
                    "Email already registered."
                )

            if existing.get(
                "mobile"
            ) == mobile:

                return (
                    False,
                    "Mobile number already registered."
                )

            return (
                False,
                "User name already registered."
            )

        # -----------------------------
        # New account
        # -----------------------------

        user = User(
            name,
            username,
            mobile,
            email,
            hash_password(password),
            role,
            "Inactive",
            False,
            False,
            False
        )

        users_collection.insert_one(
            user.to_dict()
        )

        return (
            True,
            "Member created successfully."
        )

    @staticmethod
    def get_active_members():

        return list(
            users_collection.find(
                {
                    "status": "Active",
                    "suspended": {
                        "$ne": True
                    }
                }
            ).sort(
                "name",
                1
            )
        )

    @staticmethod
    def get_inactive_members():

        return list(
            users_collection.find(
                {
                    "$or": [
                        {
                            "status": "Inactive"
                        },
                        {
                            "suspended": True
                        }
                    ]
                }
            ).sort(
                "name",
                1
            )
        )

    @staticmethod
    def get_member(member_id):

        try:

            return users_collection.find_one(
                {
                    "_id": ObjectId(member_id)
                }
            )

        except Exception:

            return None

    @staticmethod
    def activate_member(member_id):

        try:

            result = users_collection.update_one(
                {
                    "_id": ObjectId(member_id)
                },
                {
                    "$set": {
                        "status": "Active",
                        "approved": True,
                        "suspended": False
                    }
                }
            )

            if result.matched_count:

                return (
                    True,
                    "Member activated successfully."
                )

            return (
                False,
                "Member not found."
            )

        except Exception:

            return (
                False,
                "Invalid Member ID."
            )

    @staticmethod
    def deactivate_member(member_id):

        try:

            result = users_collection.update_one(
                {
                    "_id": ObjectId(member_id)
                },
                {
                    "$set": {
                        "status": "Inactive",
                        "approved": False
                    }
                }
            )

            if result.matched_count:

                return (
                    True,
                    "Member deactivated successfully."
                )

            return (
                False,
                "Member not found."
            )

        except Exception:

            return (
                False,
                "Invalid Member ID."
            )

    @staticmethod
    def lock_member(member_id):

        try:

            result = users_collection.update_one(
                {
                    "_id": ObjectId(member_id)
                },
                {
                    "$set": {
                        "locked": True
                    }
                }
            )

            if result.matched_count:

                return (
                    True,
                    "Member locked successfully."
                )

            return (
                False,
                "Member not found."
            )

        except Exception:

            return (
                False,
                "Invalid Member ID."
            )

    @staticmethod
    def unlock_member(member_id):

        try:

            result = users_collection.update_one(
                {
                    "_id": ObjectId(member_id)
                },
                {
                    "$set": {
                        "locked": False
                    }
                }
            )

            if result.matched_count:

                return (
                    True,
                    "Member unlocked successfully."
                )

            return (
                False,
                "Member not found."
            )

        except Exception:

            return (
                False,
                "Invalid Member ID."
            )

    @staticmethod
    def suspend_member(member_id):

        try:

            result = users_collection.update_one(
                {
                    "_id": ObjectId(member_id)
                },
                {
                    "$set": {
                        "suspended": True,
                        "status": "Inactive",
                        "approved": False,
                        "locked": True
                    }
                }
            )

            if result.matched_count:

                return (
                    True,
                    "Member suspended successfully."
                )

            return (
                False,
                "Member not found."
            )

        except Exception:

            return (
                False,
                "Invalid Member ID."
            )

    @staticmethod
    def delete_account(member_id):

        try:

            object_id = ObjectId(
                member_id
            )

            uid = str(
                object_id
            )

            # Check account history
            has_history = any(
                db[collection].find_one(
                    {
                        "user_id": uid
                    }
                )
                for collection in [
                    "incomes",
                    "expenses",
                    "meals",
                    "savings"
                ]
            )

            # Account has history
            if has_history:

                result = users_collection.update_one(
                    {
                        "_id": object_id
                    },
                    {
                        "$set": {
                            "suspended": True,
                            "status": "Inactive",
                            "approved": False,
                            "locked": True
                        }
                    }
                )

                if result.matched_count:

                    return (
                        True,
                        "Account has history, so it was restricted instead of permanently deleted."
                    )

                return (
                    False,
                    "Member not found."
                )

            # No history
            result = users_collection.delete_one(
                {
                    "_id": object_id
                }
            )

            if result.deleted_count:

                return (
                    True,
                    "Account permanently deleted."
                )

            return (
                False,
                "Member not found."
            )

        except Exception:

            return (
                False,
                "Invalid Member ID."
            )
