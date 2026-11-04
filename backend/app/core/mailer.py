"""Outgoing email over SMTP (STARTTLS). Call through the module so tests can replace it."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import get_settings

log = logging.getLogger(__name__)


def email_enabled() -> bool:
    return get_settings().email_enabled


def send_email(to: str, subject: str, body: str) -> None:
    """Send a plain-text email. Raises on failure."""
    s = get_settings()
    msg = EmailMessage()
    msg["From"] = formataddr((s.brand_name, s.mail_from))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid(domain=s.mail_from.split("@")[-1])
    msg.set_content(body)
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password)
        smtp.send_message(msg)
    log.info("email sent: %s", subject)
