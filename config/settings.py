"""
Application settings — loaded from environment variables.

All configuration is centralised here. Nothing should be hard-coded
in route files, service files, or templates.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """
    Encapsulates all application configuration.

    Reads values from environment variables with safe defaults.
    Use the module-level `settings` singleton to access configuration.
    """

    # ----------------------------------------------------------------
    # Database
    # ----------------------------------------------------------------

    MONGODB_URI: str = os.getenv(
        "MONGODB_URI",
        ""
    )

    DATABASE_NAME: str = os.getenv(
        "DATABASE_NAME",
        "my_expense"
    )

    # ----------------------------------------------------------------
    # Flask / Web
    # ----------------------------------------------------------------

    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "change-this-in-production"
    )

    DEBUG: bool = os.getenv(
        "DEBUG",
        "True"
    ).lower() in ("true", "1", "yes")

    # ----------------------------------------------------------------
    # Application
    # ----------------------------------------------------------------

    APP_NAME: str = "Development My Expense Software"

    DATE_FORMAT: str = "%d-%m-%Y"

    TIME_FORMAT: str = "%I:%M %p"

    # ----------------------------------------------------------------
    # Roles
    # ----------------------------------------------------------------

    ROLE_DEVELOPER: str = "Expense Developer"
    ROLE_MANAGER: str = "Manager"
    ROLE_MEMBER: str = "Member"

    VALID_ROLES: tuple = (
        ROLE_DEVELOPER,
        ROLE_MANAGER,
        ROLE_MEMBER,
    )

    # ----------------------------------------------------------------
    # Validation
    # ----------------------------------------------------------------

    def validate(self) -> None:
        """
        Raises ValueError if critical settings are missing.
        Called at application startup.
        """
        if not self.MONGODB_URI:
            raise ValueError(
                "MONGODB_URI is not set. "
                "Check your .env file."
            )

        if not self.DATABASE_NAME:
            raise ValueError(
                "DATABASE_NAME is not set. "
                "Check your .env file."
            )


# Module-level singleton — import this everywhere
settings = Settings()
