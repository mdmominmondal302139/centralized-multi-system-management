"""
Category domain model.

Represents an expense or income category.
Inherits common behaviour from BaseModel.

OOP Principles Applied:
- Inheritance: Category extends BaseModel (is-a relationship)
- Encapsulation: fields validated/normalised on construction
"""

from typing import Dict, Any
from models.base_model import BaseModel


class Category(BaseModel):
    """
    Domain model for an expense or income category.

    Categories can be used to tag expense and income records for
    filtering and reporting purposes.

    Inherits:
        BaseModel: provides created_at timestamp and to_dict contract.
    """

    def __init__(
        self,
        name: str,
        category_type: str = "expense",
        description: str = "",
        user_id: str = ""
    ) -> None:
        """
        Initialise a Category instance.

        Args:
            name:          Display name of the category.
            category_type: 'expense' or 'income'.
            description:   Optional description.
            user_id:       If set, this category belongs to one user.
                           Empty string means it is a global category.
        """
        super().__init__()

        self.name = name.strip()
        self.category_type = category_type.lower()
        self.description = description.strip()
        self.user_id = user_id

    # ----------------------------------------------------------------
    # Serialisation
    # ----------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialise the Category to a MongoDB-ready dictionary.

        Returns:
            A dict with all fields required for persistence.
        """
        return {
            "name": self.name,
            "category_type": self.category_type,
            "description": self.description,
            "user_id": self.user_id,
            "created_at": self.created_at,
        }

    def __repr__(self) -> str:
        return (
            f"<Category name={self.name!r} "
            f"type={self.category_type!r}>"
        )
