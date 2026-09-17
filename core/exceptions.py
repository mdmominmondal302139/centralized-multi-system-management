"""
Custom exception hierarchy for My Expense Software.

Defines a clean, descriptive exception hierarchy so that different
error conditions can be caught and handled at the appropriate layer
without inspecting error message strings.

OOP Principles Applied:
- Inheritance: All exceptions extend AppException (or its children)
- Abstraction: Callers catch the abstract base; handlers catch specifics
"""


class AppException(Exception):
    """
    Base exception for all application-level errors.

    All custom exceptions in this application inherit from this class,
    making it easy to catch any application error with a single clause.
    """

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        code: int = 500
    ) -> None:
        """
        Initialise the exception.

        Args:
            message: Human-readable error description.
            code: Optional HTTP-style status code for context.
        """
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self) -> str:
        return self.message


class ValidationError(AppException):
    """
    Raised when user input fails validation rules.

    Example: invalid date format, negative amount, empty required field.
    """

    def __init__(
        self,
        message: str = "Validation failed.",
        field: str = ""
    ) -> None:
        super().__init__(message, code=400)
        self.field = field


class NotFoundError(AppException):
    """
    Raised when a requested resource does not exist in the database.

    Example: expense ID not found, user not found.
    """

    def __init__(
        self,
        resource: str = "Resource",
        message: str = ""
    ) -> None:
        msg = message or f"{resource} not found."
        super().__init__(msg, code=404)
        self.resource = resource


class AuthenticationError(AppException):
    """
    Raised when login credentials are invalid or a session is expired.
    """

    def __init__(
        self,
        message: str = "Authentication failed."
    ) -> None:
        super().__init__(message, code=401)


class PermissionError(AppException):
    """
    Raised when an authenticated user attempts an action they are not
    authorised to perform.
    """

    def __init__(
        self,
        message: str = "You do not have permission to perform this action."
    ) -> None:
        super().__init__(message, code=403)


class LockError(AppException):
    """
    Raised when an operation is blocked because a record or account
    is locked.

    Example: adding an expense to a locked month.
    """

    def __init__(
        self,
        message: str = "This record is locked and cannot be modified."
    ) -> None:
        super().__init__(message, code=423)


class DuplicateError(AppException):
    """
    Raised when a record already exists (duplicate email, mobile, name).
    """

    def __init__(
        self,
        field: str = "Record",
        message: str = ""
    ) -> None:
        msg = message or f"{field} already exists."
        super().__init__(msg, code=409)
        self.field = field
