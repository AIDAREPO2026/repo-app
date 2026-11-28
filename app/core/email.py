"""Queue an email rendered from a template (security.md: never log the message body)."""

import logging
from typing import Any

from app.core.templates import templates
from workers.email import deliver

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, template: str, context: dict[str, Any]) -> None:
    """Render a template under templates/email/ and hand it to the worker to send.

    A ".html" template beside the ".txt" one is sent as the formatted version. A mail or
    queue failure never undoes the change that caused the email; it is logged.
    """
    text = templates.env.get_template(template).render(context)
    html_name = template.removesuffix(".txt") + ".html"
    html = ""
    if html_name in templates.env.list_templates():
        html = templates.env.get_template(html_name).render(context)
    try:
        # The arguments can hold a sign-in code or link, so keep them out of the worker's logs.
        deliver.apply_async((to, subject, text, html), argsrepr="(hidden)", kwargsrepr="{}")
    except Exception:  # noqa: BLE001 - any queue error must not fail the person's request
        logger.exception("Could not queue an email: %s", subject)
