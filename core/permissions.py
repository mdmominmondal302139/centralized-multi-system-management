"""
Role-based permission checking for My Expense Software.

Centralises all role/permission checks so that route handlers and
controllers can ask "can this user do X?" without needing to know
the role strings or business rules.

OOP Principles Applied:
- Encapsulation: Role strings and rules hidden inside the class
- Single Responsibility: Only answers permission questions
"""

from config.settings import settings


class PermissionChecker:
    """
    Evaluates whether a user (represented as a dict from the session
    or database) is allowed to perform a given action.

    All role-based checks should go through this class rather than
    being scattered across routes and controllers.
    """

    # ----------------------------------------------------------------
    # Role Checks
    # ----------------------------------------------------------------

    @staticmethod
    def is_developer(user: dict) -> bool:
        """
        Check whether the user has the 'Expense Developer' role.

        Args:
            user: User dict (from session or DB query).

        Returns:
            True if the user is an Expense Developer.
        """
        return (
            user.get("role") == settings.ROLE_DEVELOPER
        )

    @staticmethod
    def is_manager(user: dict) -> bool:
        """
        Check whether the user has the 'Manager' role.

        Args:
            user: User dict (from session or DB query).

        Returns:
            True if the user is a Manager.
        """
        return (
            user.get("role") == settings.ROLE_MANAGER
        )

    @staticmethod
    def is_member(user: dict) -> bool:
        """
        Check whether the user has the 'Member' role.

        Args:
            user: User dict (from session or DB query).

        Returns:
            True if the user is a regular Member.
        """
        return (
            user.get("role") == settings.ROLE_MEMBER
        )

    @staticmethod
    def is_active(user: dict) -> bool:
        """
        Check whether the user's account is active.

        Args:
            user: User dict.

        Returns:
            True if status is 'Active' and approved is True.
        """
        return (
            user.get("status") == "Active"
            and user.get("approved") is True
        )

    @staticmethod
    def is_locked(user: dict) -> bool:
        """
        Check whether the user's account is locked.

        Args:
            user: User dict.

        Returns:
            True if the account is locked.
        """
        return user.get("locked", False) is True

    # ----------------------------------------------------------------
    # Action Checks
    # ----------------------------------------------------------------

    @staticmethod
    def can_access_developer_department(user: dict) -> bool:
        """
        Only Expense Developers may access the Developer Department.

        Args:
            user: User dict.

        Returns:
            True if the user may access the developer panel.
        """
        return PermissionChecker.is_developer(user)

    @staticmethod
    def can_manage_members(user: dict) -> bool:
        """
        Only Expense Developers may create/activate/deactivate members.

        Args:
            user: User dict.

        Returns:
            True if the user may manage other members.
        """
        return PermissionChecker.is_developer(user)

    @staticmethod
    def can_unlock_expense_month(user: dict) -> bool:
        """
        Only Expense Developers may unlock an expense month.

        Members can lock their own months but cannot unlock them.

        Args:
            user: User dict.

        Returns:
            True if the user may unlock an expense month.
        """
        return PermissionChecker.is_developer(user)

    @staticmethod
    def can_write_data(user: dict) -> bool:
        """
        Check whether the user may create, update or delete records.

        A locked account cannot write any data.

        Args:
            user: User dict.

        Returns:
            True if the user may write data.
        """
        return not PermissionChecker.is_locked(user)
