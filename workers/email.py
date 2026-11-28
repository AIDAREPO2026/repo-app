"""Send queued emails, retrying while the mail server cannot be reached (P1-ACC-03)."""

import smtplib
from email.message import EmailMessage

from app.core.config import load_config
from workers.celery_app import celery_app


# smtplib's errors are OSErrors too, so this covers refusals as well as an unreachable server.
# The five retries wait 30 seconds, then 1, 2, 4 and 8 minutes, to ride out a short mail outage.
@celery_app.task(
    name="email.deliver",
    autoretry_for=(OSError,),
    retry_backoff=30,
    retry_backoff_max=8 * 60,
    retry_jitter=False,
    max_retries=5,
)
def deliver(to: str, subject: str, text: str, html: str) -> None:
    """Send one rendered email through SMTP. An empty html sends plain text only."""
    config = load_config()
    message = EmailMessage()
    message["From"] = config.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as smtp:
        if config.smtp_username:
            smtp.starttls()
            smtp.login(config.smtp_username, config.smtp_password)
        smtp.send_message(message)
