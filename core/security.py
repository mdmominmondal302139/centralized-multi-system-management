"""
Security utilities for My Expense Software.

Encapsulates all password hashing and verification logic inside a
SecurityService class. The module also exports standalone functions
for backward compatibility with utils/password_utils.py importers.

OOP Principles Applied:
- Encapsulation: Hashing algorithm details hidden inside the class
- Single Responsibility: This class only handles credential security
"""

import hashlib
import secrets
import string


class SecurityService:
    """
    Handles all password security operations.

    Encapsulates the hashing algorithm so it can be swapped out
    in one place without touching any other code.

    Current implementation: SHA-256 (compatible with existing data).
    """

    # ----------------------------------------------------------------
    # Hashing
    # ----------------------------------------------------------------

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a plain-text password.

        Args:
            password: The raw password string from the user.

        Returns:
            A hex-encoded SHA-256 digest of the password.
        """
        return hashlib.sha256(
            password.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def verify_password(
        plain_password: str,
        hashed_password: str
    ) -> bool:
        """
        Verify a plain-text password against a stored hash.

        Args:
            plain_password: The raw password entered by the user.
            hashed_password: The stored hash from the database.

        Returns:
            True if the passwords match, False otherwise.
        """
        return (
            SecurityService.hash_password(plain_password)
            == hashed_password
        )

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """
        Generate a cryptographically secure random token.

        Useful for password reset tokens or one-time codes.

        Args:
            length: Number of characters in the token.

        Returns:
            A URL-safe random string.
        """
        alphabet = (
            string.ascii_letters
            + string.digits
        )
        return "".join(
            secrets.choice(alphabet)
            for _ in range(length)
        )

    @staticmethod
    def is_strong_password(password: str) -> bool:
        """
        Check whether a password meets minimum strength requirements.

        Requirements:
        - At least 6 characters

        Args:
            password: The plain-text password to evaluate.

        Returns:
            True if the password is acceptable, False otherwise.
        """
        return len(password) >= 6


# ----------------------------------------------------------------
# Module-level functions — backward compatible with password_utils.py
# ----------------------------------------------------------------

def hash_password(password: str) -> str:
    """Backward-compatible wrapper for SecurityService.hash_password."""
    return SecurityService.hash_password(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Backward-compatible wrapper for SecurityService.verify_password."""
    return SecurityService.verify_password(
        plain_password,
        hashed_password
    )
