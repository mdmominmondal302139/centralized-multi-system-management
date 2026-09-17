"""
IncomeRepository — data access for the incomes collection.

Inherits all common CRUD from BaseRepository and adds income-specific
queries: find by user/month/year, and income lock operations.

OOP Principles Applied:
- Inheritance: Extends BaseRepository (is-a BaseRepository)
- Single Responsibility: Only handles income data access
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from repositories.base_repository import BaseRepository
from config.database import db


class IncomeRepository(BaseRepository):
    """
    Repository for the 'incomes' MongoDB collection.

    Provides all common CRUD via BaseRepository, plus income-specific
    queries and the month-lock operations via 'income_locks' collection.

    Inherits:
        BaseRepository: create, get_by_id, get_all, update, delete, etc.
    """

    def __init__(
        self,
        collection=None,
        locks_collection=None
    ) -> None:
        """
        Initialise with the incomes and income_locks collections.

        Args:
            collection:       pymongo Collection for incomes.
            locks_collection: pymongo Collection for income_locks.
        """
        super().__init__(
            collection or db["incomes"]
        )
        self._locks = (
            locks_collection or db["income_locks"]
        )

    # ----------------------------------------------------------------
    # Income-specific queries
    # ----------------------------------------------------------------

    def find_by_user(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all incomes for a user, sorted by newest first.

        Args:
            user_id: The user's ID string.

        Returns:
            List of income documents.
        """
        return self.find_many(
            {"user_id": user_id},
            sort_field="_id",
            sort_direction=-1
        )

    def find_by_user_month_year(
        self,
        user_id: str,
        month: str,
        year: int
    ) -> List[Dict[str, Any]]:
        """
        Get all incomes for a user in a specific month/year.

        Args:
            user_id: The user's ID string.
            month:   Month name (e.g. 'September').
            year:    4-digit year integer.

        Returns:
            List of income documents for that month/year.
        """
        all_records = self.find_by_user(user_id)
        result = []

        for record in all_records:
            date_value = record.get("date", "")
            try:
                date_obj = datetime.strptime(
                    date_value, "%d-%m-%Y"
                )
                rec_year = date_obj.year
                rec_month = date_obj.strftime("%B")
            except ValueError:
                rec_year = record.get("year")
                rec_month = record.get("month")

            if rec_year == year and rec_month == month:
                result.append(record)

        return result

    def find_one_by_user(
        self,
        income_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a specific income record belonging to a user.

        Args:
            income_id: String _id of the income record.
            user_id:   The owning user's ID.

        Returns:
            The income document or None.
        """
        from bson import ObjectId
        try:
            return self._collection.find_one({
                "_id": ObjectId(income_id),
                "user_id": user_id,
            })
        except Exception:
            return None

    def delete_by_user(
        self,
        income_id: str,
        user_id: str
    ) -> bool:
        """
        Delete an income record that belongs to a specific user.

        Args:
            income_id: String _id of the income.
            user_id:   Ownership check.

        Returns:
            True if found and deleted.
        """
        from bson import ObjectId
        try:
            result = self._collection.delete_one({
                "_id": ObjectId(income_id),
                "user_id": user_id,
            })
            return result.deleted_count == 1
        except Exception:
            return False

    def delete_month_records(
        self,
        ids: list
    ) -> int:
        """
        Delete multiple income records by their IDs.

        Used by IncomeService.delete_month.

        Args:
            ids: List of ObjectId values.

        Returns:
            Number of records deleted.
        """
        result = self._collection.delete_many(
            {"_id": {"$in": ids}}
        )
        return result.deleted_count

    # ----------------------------------------------------------------
    # Month lock operations
    # ----------------------------------------------------------------

    def is_month_locked(
        self,
        user_id: str,
        month: str,
        year: int
    ) -> bool:
        """
        Check whether an income month is locked for a user.

        Args:
            user_id: The user's ID.
            month:   Month name string (e.g. 'September').
            year:    4-digit year integer.

        Returns:
            True if the month is locked.
        """
        lock = self._locks.find_one({
            "user_id": user_id,
            "month": month,
            "year": year,
        })
        return lock is not None

    def lock_month(
        self,
        user_id: str,
        month: str,
        year: int
    ) -> bool:
        """
        Lock an income month for a user.

        Args:
            user_id: The user's ID.
            month:   Month name string.
            year:    4-digit year integer.

        Returns:
            True if newly locked; False if already locked.
        """
        existing = self._locks.find_one({
            "user_id": user_id,
            "month": month,
            "year": year,
        })
        if existing:
            return False
        self._locks.insert_one({
            "user_id": user_id,
            "month": month,
            "year": year,
        })
        return True

    def toggle_month_lock(
        self,
        user_id: str,
        month: str,
        year: int
    ) -> bool:
        """
        Toggle the lock state for an income month.

        Args:
            user_id: The user's ID.
            month:   Month name string.
            year:    4-digit year integer.

        Returns:
            True if now locked; False if now unlocked.
        """
        existing = self._locks.find_one({
            "user_id": user_id,
            "month": month,
            "year": year,
        })
        if existing:
            self._locks.delete_one({"_id": existing["_id"]})
            return False
        self._locks.insert_one({
            "user_id": user_id,
            "month": month,
            "year": year,
        })
        return True
