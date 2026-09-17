import re

from config.database import users_collection
from utils.password_utils import verify_password


class AuthService:

    @staticmethod
    def _valid_username(username):
        """
        Username rules:
        - lowercase letters only
        - numbers allowed
        - underscore allowed
        - no spaces
        - no uppercase letters
        - no email
        - no mobile number format
        """

        if not username:
            return False

        return bool(
            re.fullmatch(
                r"[a-z0-9_]+",
                username
            )
        )

    @staticmethod
    def _valid_password(password):
        """
        Password must contain at least 8 characters.
        """

        return bool(password) and len(password) >= 8

    @staticmethod
    def register(
        name,
        username,
        mobile,
        email,
        password
    ):
        """
        Public registration is disabled.

        Accounts can only be created by
        Expense Developer from Developer Department.
        """

        return (
            False,
            "Public registration is disabled. "
            "Only Expense Developer can create accounts."
        )

    @staticmethod
    def login(
        login_value,
        password
    ):
        """
        Login is allowed ONLY with username.

        Name, mobile and email cannot be used.
        """

        login_value = str(
            login_value or ""
        ).strip()

        password = str(
            password or ""
        )

        # -----------------------------------------
        # Username required
        # -----------------------------------------

        if not login_value:
            return (
                False,
                "Username is required.",
                None
            )

        # -----------------------------------------
        # Username must be lowercase
        # -----------------------------------------

        if login_value != login_value.lower():
            return (
                False,
                "Username must be lowercase.",
                None
            )

        # -----------------------------------------
        # Username format validation
        # -----------------------------------------

        if not AuthService._valid_username(
            login_value
        ):
            return (
                False,
                "Invalid username. "
                "Use lowercase letters, numbers and underscore only.",
                None
            )

        # -----------------------------------------
        # Password validation
        # -----------------------------------------

        if not AuthService._valid_password(
            password
        ):
            return (
                False,
                "Password must be at least 8 characters.",
                None
            )

        # -----------------------------------------
        # IMPORTANT:
        # Login search is ONLY by username.
        #
        # Name / Mobile / Email are NOT used.
        # -----------------------------------------

        user = users_collection.find_one(
            {
                "username": login_value
            }
        )

        # -----------------------------------------
        # Username not found
        # -----------------------------------------

        if not user:
            return (
                False,
                "Invalid username or password.",
                None
            )

        # -----------------------------------------
        # Password verification
        # -----------------------------------------

        if not verify_password(
            password,
            user.get("password", "")
        ):
            return (
                False,
                "Invalid username or password.",
                None
            )

        # -----------------------------------------
        # Suspended account
        # -----------------------------------------

        if user.get("suspended") is True:
            return (
                False,
                "Your account is suspended.",
                None
            )

        # -----------------------------------------
        # Account activation check
        # -----------------------------------------

        if (
            user.get("status") != "Active"
            or user.get("approved") is not True
        ):
            return (
                False,
                "Your account is inactive. "
                "Please wait for Expense Developer approval.",
                None
            )

        # -----------------------------------------
        # Successful login
        # -----------------------------------------

        return (
            True,
            "Login successful!",
            user
        )