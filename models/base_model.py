"""
BaseModel — shared foundation for all domain models.

Every domain model (User, Expense, Income, Meal, Saving, Category)
inherits from this class to gain:
  - A consistent created_at timestamp
  - An abstract to_dict() contract enforced by @abstractmethod
  - A human-readable __repr__

OOP Principles Applied:
- Abstraction: to_dict() is declared abstract; subclasses define HOW
- Inheritance: All models share created_at and __repr__ automatically
- Encapsulation: _created_at is private; exposed via property
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any


class BaseModel(ABC):
    """
    Abstract base class for all domain models.

    Provides a common created_at timestamp and enforces the to_dict()
    contract on every subclass. This ensures every model can be
    serialised to a dict for MongoDB insertion.

    Subclasses MUST implement:
        to_dict() -> Dict[str, Any]
    """

    def __init__(self) -> None:
        """
        Initialise the base model with a creation timestamp.
        """
        self._created_at: datetime = datetime.now()

    # ----------------------------------------------------------------
    # Properties
    # ----------------------------------------------------------------

    @property
    def created_at(self) -> datetime:
        """
        Creation timestamp (read-only).

        Returns:
            The datetime when this instance was created.
        """
        return self._created_at

    # ----------------------------------------------------------------
    # Abstract Interface
    # ----------------------------------------------------------------

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialise the model to a dictionary suitable for MongoDB.

        Every subclass must implement this method.
        The returned dict must include all fields that should be
        persisted to the database.

        Returns:
            A dictionary representation of the model.
        """
        pass

    # ----------------------------------------------------------------
    # Common behaviour
    # ----------------------------------------------------------------

    def __repr__(self) -> str:
        """
        Return a developer-friendly string representation.

        Returns:
            A string showing the class name and created_at timestamp.
        """
        return (
            f"<{self.__class__.__name__} "
            f"created_at={self._created_at.strftime('%Y-%m-%d %H:%M:%S')}>"
        )
