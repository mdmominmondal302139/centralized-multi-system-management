"""
ExpenseRepository — data access for the expenses collection.

Inherits all common CRUD from BaseRepository and adds expense-specific
queries: find by user_id, find by month, and expense lock operations.

OOP Principles Applied:
- Inheritance: Extends BaseRepository (is-a BaseRepository)
- Single Responsibility: Only handles expense data access
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from repositories.base_repository import BaseRepository
from config.database import db


class ExpenseRepository(BaseRepository):
    """
    Repository for the 'expenses' MongoDB collection.

    Provides all common CRUD via BaseRepository, plus expense-specific
    queries and the month-lock operations via 'expense_locks' collection.

    Inherits:
        BaseRepository: create, get_by_id, get_all, update, delete, etc.
    """

    def __init__(
        self,
        collection=None,
        locks_collection=None
    ) -> None:
        """
        Initialise with the expenses and expense_locks collections.

        Args:
            collection:       pymongo Collection for expenses.
            locks_collection: pymongo Collection for expense_locks.
        """
        super().__init__(
            collection or db["expenses"]
        )
        self._locks = (
            locks_collection or db["expense_locks"]
        )

    # ----------------------------------------------------------------
    # Expense-specific queries
    # ----------------------------------------------------------------

    def find_by_user(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all expenses for a user, sorted by newest first.

        Args:
            user_id: The user's ID string.

        Returns:
            List of expense documents.
        """
        return self.find_many(
            {"user_id": user_id},
            sort_field="_id",
            sort_direction=-1
        )

    def find_by_user_and_month(
        self,
        user_id: str,
        month_key: str
    ) -> List[Dict[str, Any]]:
        """
        Get all expenses for a user in a specific month.

        Args:
            user_id:   The user's ID string.
            month_key: Month in 'YYYY-MM' format.

        Returns:
            List of expense documents for that month.
        """
        return self.find_many(
            {"user_id": user_id, "month": month_key},
            sort_field="_id",
            sort_direction=-1
        )

    def find_one_by_user(
        self,
        expense_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a specific expense belonging to a user.

        Args:
            expense_id: String _id of the expense.
            user_id:    The owning user's ID.

        Returns:
            The expense document or None.
        """
        from bson import ObjectId
        try:
            return self._collection.find_one({
                "_id": ObjectId(expense_id),
                "user_id": user_id,
            })
        except Exception:
            return None

    def update_by_user(
        self,
        expense_id: str,
        user_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Update an expense document that belongs to a specific user.

        Args:
            expense_id: String _id of the expense.
            user_id:    The owning user's ID (ownership check).
            data:       Fields to update.

        Returns:
            True if matched and updated.
        """
        from bson import ObjectId
        try:
            result = self._collection.update_one(
                {
                    "_id": ObjectId(expense_id),
                    "user_id": user_id,
                },
                {"$set": data}
            )
            return result.matched_count == 1
        except Exception:
            return False

    def delete_by_user(
        self,
        expense_id: str,
        user_id: str
    ) -> bool:
        """
        Delete an expense document that belongs to a specific user.

        Args:
            expense_id: String _id of the expense.
            user_id:    The owning user's ID (ownership check).

        Returns:
            True if found and deleted.
        """
        from bson import ObjectId
        try:
            result = self._collection.delete_one({
                "_id": ObjectId(expense_id),
                "user_id": user_id,
            })
            return result.deleted_count == 1
        except Exception:
            return False

    # ----------------------------------------------------------------
    # Month lock operations
    # ----------------------------------------------------------------

    def is_month_locked(
        self,
        user_id: str,
        month_key: str
    ) -> bool:
        """
        Check whether a month is locked for a user.

        Args:
            user_id:   The user's ID.
            month_key: Month in 'YYYY-MM' format.

        Returns:
            True if the month is locked.
        """
        record = self._locks.find_one({
            "user_id": user_id,
            "month": month_key,
        })
        if record:
            return record.get("locked", False) is True
        return False

    def lock_month(
        self,
        user_id: str,
        month_key: str
    ) -> bool:
        """
        Lock an expense month for a user.

        Args:
            user_id:   The user's ID.
            month_key: Month in 'YYYY-MM' format.

        Returns:
            True if the lock was applied.
        """
        self._locks.update_one(
            {"user_id": user_id, "month": month_key},
            {
                "$set": {
                    "user_id": user_id,
                    "month": month_key,
                    "locked": True,
                    "updated_at": datetime.now(),
                }
            },
            upsert=True
        )
        return True

    def unlock_month(
        self,
        user_id: str,
        month_key: str
    ) -> bool:
        """
        Unlock an expense month for a user.

        Args:
            user_id:   The user's ID.
            month_key: Month in 'YYYY-MM' format.

        Returns:
            True if the unlock was applied.
        """
        self._locks.update_one(
            {"user_id": user_id, "month": month_key},
            {
                "$set": {
                    "locked": False,
                    "updated_at": datetime.now(),
                }
            }
        )
        return True
