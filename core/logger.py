"""
Structured logging for My Expense Software.

Provides a reusable AppLogger class that wraps Python's standard
logging module. All application components should use this logger
instead of bare print() calls for operational events.

OOP Principles Applied:
- Encapsulation: Logger configuration hidden inside AppLogger
- Single Responsibility: Only handles log output
"""

import logging
import os
from datetime import datetime


class AppLogger:
    """
    Configured logger for My Expense Software.

    Wraps Python's logging module with a consistent format and
    log level. Use the module-level `logger` singleton throughout
    the application.

    Usage:
        from core.logger import logger
        logger.info("Expense added for user %s", user_id)
    """

    def __init__(
        self,
        name: str = "my_expense",
        level: int = logging.INFO
    ) -> None:
        """
        Initialise the logger.

        Args:
            name: Logger name (appears in log output).
            level: Minimum severity level to emit.
        """
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)

        if not self._logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Configure console and optional file handlers."""

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            fmt=(
                "[%(asctime)s] %(levelname)-8s "
                "%(name)s — %(message)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

    # ----------------------------------------------------------------
    # Logging methods — delegate to the internal logger
    # ----------------------------------------------------------------

    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a DEBUG-level message."""
        self._logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs) -> None:
        """Log an INFO-level message."""
        self._logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs) -> None:
        """Log a WARNING-level message."""
        self._logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs) -> None:
        """Log an ERROR-level message."""
        self._logger.error(message, *args, **kwargs)

    def exception(self, message: str, *args, **kwargs) -> None:
        """Log an ERROR with a full exception traceback."""
        self._logger.exception(message, *args, **kwargs)


# Module-level singleton — import this everywhere
logger = AppLogger()
