"""
Models package for My Expense Software.

All domain models live here and inherit from BaseModel.
"""

from models.base_model import BaseModel
from models.user import User
from models.expense import Expense
from models.income import Income
from models.meal import Meal
from models.saving import Saving
from models.category import Category

__all__ = [
    "BaseModel",
    "User",
    "Expense",
    "Income",
    "Meal",
    "Saving",
    "Category",
]
