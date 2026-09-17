"""
BaseRepository — common MongoDB CRUD operations.

Implements the RepositoryInterface contract with concrete MongoDB
behaviour that all child repositories inherit. Child repositories
only need to add entity-specific queries; common CRUD comes for free.

OOP Principles Applied:
- Inheritance: Child repos inherit all CRUD from BaseRepository
- Abstraction: Implements the RepositoryInterface contract
- Encapsulation: MongoDB collection is private (_collection)
- Dependency Injection: Collection passed in constructor
"""

from typing import Any, Dict, List, Optional
from bson import ObjectId
from bson.errors import InvalidId

from interfaces.repository import RepositoryInterface


class BaseRepository(RepositoryInterface):
    """
    Concrete base repository providing common MongoDB CRUD operations.

    All entity-specific repositories (UserRepository, ExpenseRepository,
    etc.) inherit from this class and receive create/read/update/delete
    for free. Entity-specific queries are added in the subclass.

    Constructor Injection:
        Pass the MongoDB collection object at construction time.
        This makes the repository testable by injecting a mock.
    """

    def __init__(self, collection) -> None:
        """
        Initialise the repository with a MongoDB collection.

        Args:
            collection: A pymongo Collection object.
        """
        self._collection = collection

    # ----------------------------------------------------------------
    # RepositoryInterface implementation
    # ----------------------------------------------------------------

    def create(self, data: Dict[str, Any]) -> Any:
        """
        Insert a new document into the collection.

        Args:
            data: Field values to insert.

        Returns:
            The pymongo InsertOneResult object.
        """
        return self._collection.insert_one(data)

    def get_by_id(
        self,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Find a document by its MongoDB _id.

        Args:
            item_id: String form of the ObjectId.

        Returns:
            The document dict or None if not found / invalid id.
        """
        try:
            return self._collection.find_one(
                {"_id": ObjectId(item_id)}
            )
        except (InvalidId, Exception):
            return None

    def get_all(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_field: str = "_id",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all documents matching optional filters.

        Args:
            filters:        MongoDB query dict. None returns all docs.
            sort_field:     Field name to sort by (default: _id).
            sort_direction: 1 for ascending, -1 for descending.

        Returns:
            List of matching document dicts.
        """
        query = filters or {}
        return list(
            self._collection.find(query).sort(
                sort_field,
                sort_direction
            )
        )

    def update(
        self,
        item_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """
        Update a document by its _id using $set.

        Args:
            item_id: String form of the ObjectId.
            data:    Fields to update.

        Returns:
            True if a document was matched and updated.
        """
        try:
            result = self._collection.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": data}
            )
            return result.matched_count == 1
        except (InvalidId, Exception):
            return False

    def delete(self, item_id: str) -> bool:
        """
        Delete a document by its _id.

        Args:
            item_id: String form of the ObjectId.

        Returns:
            True if a document was found and deleted.
        """
        try:
            result = self._collection.delete_one(
                {"_id": ObjectId(item_id)}
            )
            return result.deleted_count == 1
        except (InvalidId, Exception):
            return False

    # ----------------------------------------------------------------
    # Convenience helpers available to all child repositories
    # ----------------------------------------------------------------

    def find_one(
        self,
        filters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find a single document matching the given filters.

        Args:
            filters: MongoDB query dict.

        Returns:
            The first matching document, or None.
        """
        return self._collection.find_one(filters)

    def find_many(
        self,
        filters: Dict[str, Any],
        sort_field: str = "_id",
        sort_direction: int = -1
    ) -> List[Dict[str, Any]]:
        """
        Find all documents matching the given filters.

        Args:
            filters:        MongoDB query dict.
            sort_field:     Field name to sort by.
            sort_direction: 1 ascending, -1 descending.

        Returns:
            List of matching document dicts.
        """
        return list(
            self._collection.find(filters).sort(
                sort_field,
                sort_direction
            )
        )

    def update_by_filter(
        self,
        filters: Dict[str, Any],
        data: Dict[str, Any],
        upsert: bool = False
    ) -> bool:
        """
        Update a document matching custom filters.

        Args:
            filters: MongoDB query dict to identify the document.
            data:    Fields to set.
            upsert:  If True, insert the document if not found.

        Returns:
            True if a document was matched.
        """
        result = self._collection.update_one(
            filters,
            {"$set": data},
            upsert=upsert
        )
        return result.matched_count >= 1 or (
            upsert and result.upserted_id is not None
        )

    def delete_many(
        self,
        filters: Dict[str, Any]
    ) -> int:
        """
        Delete all documents matching the given filters.

        Args:
            filters: MongoDB query dict.

        Returns:
            Number of documents deleted.
        """
        result = self._collection.delete_many(filters)
        return result.deleted_count

    def count(
        self,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count documents matching the given filters.

        Args:
            filters: MongoDB query dict. None counts all.

        Returns:
            Number of matching documents.
        """
        return self._collection.count_documents(
            filters or {}
        )
