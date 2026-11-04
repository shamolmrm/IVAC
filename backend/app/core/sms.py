"""Outgoing SMS. Call through the module so tests can replace it.

Disabled until a provider is configured (SMS_PROVIDER). Each Bangladeshi provider has its own
HTTP API; an adapter is added here once the owner picks one and shares its documentation.
`console` is for local development only: it logs the message instead of sending it.
"""

import logging

from app.core.config import get_settings

log = logging.getLogger(__name__)


class SmsError(RuntimeError):
    pass


def sms_enabled() -> bool:
    s = get_settings()
    if s.sms_provider == "console":
        return not s.is_production  # never "send" codes to logs in production
    return s.sms_provider in _ADAPTERS


def send_sms(phone: str, message: str) -> None:
    """Send one SMS to a +8801XXXXXXXXX number. Raises SmsError on failure."""
    s = get_settings()
    if s.sms_provider == "console" and not s.is_production:
        log.warning("SMS (console, not sent) to %s: %s", phone, message)
        return
    adapter = _ADAPTERS.get(s.sms_provider)
    if adapter is None:
        raise SmsError("SMS provider is not configured.")
    adapter(phone, message)


# provider name -> function(phone, message); filled in when a provider is chosen
_ADAPTERS: dict = {}
