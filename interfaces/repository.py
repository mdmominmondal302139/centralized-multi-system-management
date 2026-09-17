"""
Repository interface — abstract contract for all data repositories.

Defines WHAT a repository must do (create, read, update, delete).
Concrete implementations define HOW it is done (MongoDB, SQL, etc.).

OOP Principles Applied:
- Abstraction: Abstract methods declare the contract without implementation
- Polymorphism: Any class implementing this interface is interchangeable
- Open/Closed: New repository backends can be added without changing services
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class RepositoryInterface(ABC):
    """
    Abstract contract for all data repository classes.

    Every concrete repository (UserRepository, ExpenseRepository, etc.)
    must implement these methods. Services depend on this interface,
    not on concrete repository implementations (Dependency Inversion).

    Subclasses MUST implement:
        create(data)
        get_by_id(item_id)
        get_all(filters)
        update(item_id, data)
        delete(item_id)
    """

    @abstractmethod
    def create(self, data: Dict[str, Any]) -> Any:
        """
        Persist a new record to the data store.

        Args:
            data: Dictionary of field values to insert.

        Returns:
            The result of the insert operation (implementation-specific).
        """
        pass

    @abstractmethod
    def get_by_id(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a single record by its unique identifier.

        Args:
            item_id: The string representation of the record's ID.

        Returns:
            The record as a dict, or None if not found.
        """
        pass

    @abstractmethod
    def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all records matching the given filters.

        Args:
            filters: Optional dict of MongoDB query filters.
                     If None or empty, returns all records.

        Returns:
            A list of matching records as dicts.
        """
        pass

    @abstractmethod
    def update(
        self,
        item_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Update an existing record by its unique identifier.

        Args:
            item_id: The string representation of the record's ID.
            data:    Dictionary of fields to update ($set values).

        Returns:
            True if the record was found and updated, False otherwise.
        """
        pass

    @abstractmethod
    def delete(self, item_id: str) -> bool:
        """
        Delete a record by its unique identifier.

        Args:
            item_id: The string representation of the record's ID.

        Returns:
            True if the record was found and deleted, False otherwise.
        """
        pass
