"""
Notification interface — abstract contract for notification implementations.

Defines WHAT a notification sender must do.
Concrete implementations define HOW it is delivered (email, SMS, etc.).

OOP Principles Applied:
- Abstraction: Only the 'send' contract is defined here
- Open/Closed: New channels (email, push, etc.) can be added without
               changing notification callers
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class NotificationInterface(ABC):
    """
    Abstract contract for notification delivery implementations.

    Any class that delivers notifications to users (email, SMS, in-app)
    must implement the send() method. Callers only depend on this
    interface, making notification channels interchangeable.

    Subclasses MUST implement:
        send(recipient, subject, body)
    """

    @abstractmethod
    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: Any
    ) -> bool:
        """
        Send a notification to the recipient.

        Args:
            recipient: Destination identifier (email, phone number, user_id).
            subject:   Short title or subject for the notification.
            body:      Full notification body text.
            **kwargs:  Channel-specific additional parameters.

        Returns:
            True if the notification was delivered successfully.
        """
        pass

    @abstractmethod
    def send_bulk(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        **kwargs: Any
    ) -> Dict[str, bool]:
        """
        Send a notification to multiple recipients.

        Args:
            recipients: List of destination identifiers.
            subject:    Short title or subject.
            body:       Full notification body text.
            **kwargs:   Channel-specific additional parameters.

        Returns:
            A dict mapping each recipient to a delivery success flag.
        """
        pass


class ConsoleNotification(NotificationInterface):
    """
    Console (stdout) implementation of the notification interface.

    Used during development and testing. Prints notifications to the
    console instead of actually sending them.

    This demonstrates Polymorphism — the same interface, different
    behaviour depending on which implementation is used.
    """

    def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        **kwargs: Any
    ) -> bool:
        """
        Print the notification to the console.

        Args:
            recipient: Destination identifier.
            subject:   Notification subject.
            body:      Notification body.

        Returns:
            Always True (console output never fails).
        """
        print(
            f"\n[NOTIFICATION] To: {recipient}\n"
            f"Subject: {subject}\n"
            f"Body: {body}\n"
        )
        return True

    def send_bulk(
        self,
        recipients: List[str],
        subject: str,
        body: str,
        **kwargs: Any
    ) -> Dict[str, bool]:
        """
        Print the notification for each recipient to the console.

        Returns:
            Dict mapping each recipient to True.
        """
        results = {}
        for recipient in recipients:
            results[recipient] = self.send(
                recipient,
                subject,
                body,
                **kwargs
            )
        return results
