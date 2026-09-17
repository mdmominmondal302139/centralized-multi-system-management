"""
UserRepository — data access for the users collection.

Handles all user-specific database queries.
"""

from typing import Any, Dict, List, Optional

from repositories.base_repository import BaseRepository
from config.database import db


class UserRepository(BaseRepository):

    def __init__(self, collection=None) -> None:
        super().__init__(collection or db["users"])

    # ------------------------------------------------------------
    # Username
    # ------------------------------------------------------------

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return self.find_one({
            "username": username.strip()
        })

    # ------------------------------------------------------------
    # Name
    # ------------------------------------------------------------

    def find_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        return self.find_one({
            "name": name
        })

    # ------------------------------------------------------------
    # Mobile
    # ------------------------------------------------------------

    def find_by_mobile(self, mobile: str) -> Optional[Dict[str, Any]]:
        return self.find_one({
            "mobile": mobile
        })

    # ------------------------------------------------------------
    # Email
    # ------------------------------------------------------------

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self.find_one({
            "email": email
        })

    # ------------------------------------------------------------
    # Username / Name / Mobile compatibility search
    # ------------------------------------------------------------

    def find_by_name_or_mobile(
        self,
        login_value: str
    ) -> Optional[Dict[str, Any]]:

        return self.find_one({
            "$or": [
                {"username": login_value},
                {"name": login_value},
                {"mobile": login_value},
            ]
        })

    # ------------------------------------------------------------
    # Registration duplicate check
    # ------------------------------------------------------------

    def find_by_username_or_name_or_mobile_or_email(
        self,
        username: str,
        name: str,
        mobile: str,
        email: str
    ) -> Optional[Dict[str, Any]]:

        return self.find_one({
            "$or": [
                {"username": username},
                {"name": name},
                {"mobile": mobile},
                {"email": email},
            ]
        })

    # ------------------------------------------------------------
    # Old compatibility method
    # ------------------------------------------------------------

    def find_by_name_or_mobile_or_email(
        self,
        name: str,
        mobile: str,
        email: str
    ) -> Optional[Dict[str, Any]]:

        return self.find_one({
            "$or": [
                {"name": name},
                {"mobile": mobile},
                {"email": email},
            ]
        })

    # ------------------------------------------------------------
    # Status
    # ------------------------------------------------------------

    def get_by_status(
        self,
        status: str
    ) -> List[Dict[str, Any]]:

        return self.find_many(
            {"status": status},
            sort_field="name",
            sort_direction=1
        )

    # ------------------------------------------------------------
    # Active members
    # ------------------------------------------------------------

    def get_active_members(self) -> List[Dict[str, Any]]:
        return self.get_by_status("Active")

    # ------------------------------------------------------------
    # Inactive members
    # ------------------------------------------------------------

    def get_inactive_members(self) -> List[Dict[str, Any]]:
        return self.get_by_status("Inactive")

    # ------------------------------------------------------------
    # Activate
    # ------------------------------------------------------------

    def activate(self, user_id: str) -> bool:
        return self.update(
            user_id,
            {
                "status": "Active",
                "approved": True
            }
        )

    # ------------------------------------------------------------
    # Deactivate
    # ------------------------------------------------------------

    def deactivate(self, user_id: str) -> bool:
        return self.update(
            user_id,
            {
                "status": "Inactive",
                "approved": False
            }
        )

    # ------------------------------------------------------------
    # Lock / Unlock
    # ------------------------------------------------------------

    def set_locked(
        self,
        user_id: str,
        locked: bool
    ) -> bool:

        return self.update(
            user_id,
            {
                "locked": locked
            }
        )

    # ------------------------------------------------------------
    # Check locked
    # ------------------------------------------------------------

    def is_user_locked(
        self,
        user_id: str
    ) -> bool:

        user = self.get_by_id(user_id)

        if not user:
            return False

        return user.get("locked", False) is True