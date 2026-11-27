"""Send an email from a plain-text template (security.md: never log the message body)."""

import smtplib
from email.message import EmailMessage
from typing import Any

from app.core.config import load_config
from app.core.templates import templates


def send_email(to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    """Render a template under templates/email/ and send it through SMTP now.

    ponytail: sends inside the request, so a mail server outage shows the person an error page;
    P1-ACC-03 moves sending to a Celery task with retries, keeping this signature.
    """
    config = load_config()
    message = EmailMessage()
    message["From"] = config.mail_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(templates.env.get_template(template).render(context))
    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=10) as smtp:
        if config.smtp_username:
            smtp.starttls()
            smtp.login(config.smtp_username, config.smtp_password)
        smtp.send_message(message)
