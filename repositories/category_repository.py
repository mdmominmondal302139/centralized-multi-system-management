"""
CategoryRepository — data access for the categories collection.

Inherits all common CRUD from BaseRepository and adds category-specific
queries: find by type, find by user, find global categories.

OOP Principles Applied:
- Inheritance: Extends BaseRepository (is-a BaseRepository)
- Single Responsibility: Only handles category data access
"""

from typing import Any, Dict, List, Optional

from repositories.base_repository import BaseRepository
from config.database import db


class CategoryRepository(BaseRepository):
    """
    Repository for the 'categories' MongoDB collection.

    Provides all common CRUD via BaseRepository, plus category-specific
    queries used by CategoryService.

    Inherits:
        BaseRepository: create, get_by_id, get_all, update, delete, etc.
    """

    def __init__(self, collection=None) -> None:
        """
        Initialise with the categories collection.

        Args:
            collection: pymongo Collection. Defaults to db["categories"].
        """
        super().__init__(
            collection or db["categories"]
        )

    # ----------------------------------------------------------------
    # Category-specific queries
    # ----------------------------------------------------------------

    def find_by_type(
        self,
        category_type: str
    ) -> List[Dict[str, Any]]:
        """
        Get all categories of a given type (expense or income).

        Args:
            category_type: 'expense' or 'income'.

        Returns:
            List of category documents sorted by name.
        """
        return self.find_many(
            {"category_type": category_type},
            sort_field="name",
            sort_direction=1
        )

    def find_by_user(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all categories belonging to a specific user.

        Args:
            user_id: The user's ID string.

        Returns:
            List of user-specific category documents.
        """
        return self.find_many(
            {"user_id": user_id},
            sort_field="name",
            sort_direction=1
        )

    def find_global(self) -> List[Dict[str, Any]]:
        """
        Get all global (shared) categories (user_id is empty string).

        Returns:
            List of global category documents.
        """
        return self.find_many(
            {"user_id": ""},
            sort_field="name",
            sort_direction=1
        )

    def find_by_name(
        self,
        name: str,
        category_type: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Find a category by name and optional type.

        Args:
            name:          The category name to search for.
            category_type: Optional type filter.

        Returns:
            The first matching category document or None.
        """
        filters: Dict[str, Any] = {"name": name}
        if category_type:
            filters["category_type"] = category_type
        return self.find_one(filters)
