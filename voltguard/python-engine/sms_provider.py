"""
VoltGuard Phase 1E - SMS Provider Abstraction
Non-functional integration layer for Phase 1, ready for Phase 2 provider hookup.
"""

from abc import ABC, abstractmethod
from datetime import datetime


class SMSProvider(ABC):
    """Abstract SMS provider interface."""

    @abstractmethod
    def send_alert(self, phone_number: str, message_body: str) -> bool:
        """Send SMS alert and return success state."""
        raise NotImplementedError()

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when provider is ready for use."""
        raise NotImplementedError()


class ArkeselSMSProvider(SMSProvider):
    """
    Arkesel API provider (Phase 2 implementation placeholder).
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

    def send_alert(self, phone_number: str, message_body: str) -> bool:
        # Phase 2: Replace with real HTTP request to Arkesel.
        return bool(self.api_key and phone_number and message_body)

    def is_configured(self) -> bool:
        return bool(self.api_key)


class MockSMSProvider(SMSProvider):
    """
    Phase 1 mock provider: logs SMS payload to console.
    """

    def send_alert(self, phone_number: str, message_body: str) -> bool:
        print(f"[MOCK SMS] To: {phone_number}\nMessage: {message_body}")
        return True

    def is_configured(self) -> bool:
        return True


def should_send_sms(current_state: str, relay_status: str, last_sms_timestamp: datetime, duplicate_window: int) -> bool:
    """
    Send SMS only after confirmed shutdown, with duplicate suppression.
    """
    if current_state != "CRITICAL" or relay_status != "OFF":
        return False

    if last_sms_timestamp is None:
        return True

    elapsed_seconds = (datetime.now() - last_sms_timestamp).total_seconds()
    return elapsed_seconds > duplicate_window


def format_sms_message(current: float, temperature: float, timestamp: datetime) -> str:
    """Format a standard alert message."""
    return (
        "ALERT: Critical Electrical Condition Detected\n"
        f"Current: {current:.2f}A\n"
        f"Temperature: {temperature:.2f}C\n"
        "Action: Power Supply Turned OFF\n"
        f"Time: {timestamp.strftime('%H:%M:%S')}"
    )
