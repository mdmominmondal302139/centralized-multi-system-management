"""
CategoryService — category management business logic.

Handles creating, retrieving, and deleting categories.

OOP Principles Applied:
- Dependency Injection: CategoryRepository injected via constructor
- Single Responsibility: Only handles category operations
"""

from typing import Any, Dict, List, Optional, Tuple

from models.category import Category
from repositories.category_repository import CategoryRepository
from core.logger import logger


class CategoryService:
    """
    Business logic for category management.

    Categories can be global (shared across all users) or
    user-specific (belonging to one user).
    """

    def __init__(
        self,
        category_repository: Optional[CategoryRepository] = None
    ) -> None:
        """
        Initialise with injected repository.

        Args:
            category_repository: Defaults to CategoryRepository().
        """
        self._category_repo = (
            category_repository or CategoryRepository()
        )

    def create_category(
        self,
        name: str,
        category_type: str = "expense",
        description: str = "",
        user_id: str = ""
    ) -> Tuple[bool, str]:
        """
        Create a new category.

        Args:
            name:          Category name.
            category_type: 'expense' or 'income'.
            description:   Optional description.
            user_id:       Owner user ID or '' for global.

        Returns:
            (success: bool, message: str)
        """
        existing = self._category_repo.find_by_name(
            name, category_type
        )
        if existing:
            return False, "Category already exists."

        category = Category(
            name=name,
            category_type=category_type,
            description=description,
            user_id=user_id,
        )
        self._category_repo.create(category.to_dict())
        logger.info("Category created: %s (%s)", name, category_type)
        return True, "Category created successfully!"

    def get_categories(
        self,
        category_type: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Get categories, optionally filtered by type.

        Args:
            category_type: 'expense', 'income', or '' for all.

        Returns:
            List of category documents.
        """
        if category_type:
            return self._category_repo.find_by_type(category_type)
        return self._category_repo.get_all(
            sort_field="name", sort_direction=1
        )

    def get_expense_categories(self) -> List[Dict[str, Any]]:
        """Return all expense categories."""
        return self._category_repo.find_by_type("expense")

    def get_income_categories(self) -> List[Dict[str, Any]]:
        """Return all income categories."""
        return self._category_repo.find_by_type("income")

    def delete_category(
        self,
        category_id: str
    ) -> Tuple[bool, str]:
        """
        Delete a category.

        Args:
            category_id: String _id of the category.

        Returns:
            (success: bool, message: str)
        """
        deleted = self._category_repo.delete(category_id)
        if deleted:
            logger.info("Category deleted: %s", category_id)
            return True, "Category deleted successfully!"
        return False, "Category not found."
