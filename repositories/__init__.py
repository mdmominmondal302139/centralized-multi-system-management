"""
Repositories package for My Expense Software.

All repository classes live here. Each repository is responsible
for data access to one MongoDB collection.
"""

from repositories.base_repository import BaseRepository
from repositories.user_repository import UserRepository
from repositories.expense_repository import ExpenseRepository
from repositories.income_repository import IncomeRepository
from repositories.category_repository import CategoryRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "ExpenseRepository",
    "IncomeRepository",
    "CategoryRepository",
]
