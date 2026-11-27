"""Friendly error pages that never reveal internal details."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.exceptions import HTTPException

from app.core.navigation import nav_for
from app.core.templates import templates

logger = logging.getLogger(__name__)

# Message ids for the pages the spec names. Any other status gets the generic text.
ERROR_TEXT = {
    403: ("Access denied", "You do not have permission to open this page."),
    404: ("Page not found", "The page you asked for does not exist or has moved."),
    500: ("Something went wrong", "We could not complete your request. Please try again later."),
}
GENERIC_TEXT = ("Something went wrong", "We could not complete your request.")


def render_error(request: Request, status_code: int) -> HTMLResponse:
    """Render the error page for a status code, with the public menu only."""
    title, message = ERROR_TEXT.get(status_code, GENERIC_TEXT)
    context = {"status_code": status_code, "title": title, "message": message, "nav": nav_for(None)}
    return templates.TemplateResponse(request, "errors/error.html", context, status_code=status_code)


def http_error(request: Request, exc: Exception) -> Response:
    """Follow a guard's redirect to sign in, else show the friendly page for 403, 404 and other errors."""
    if isinstance(exc, HTTPException) and exc.status_code == 303 and exc.headers:
        return RedirectResponse(exc.headers["Location"], status_code=303)
    status_code = exc.status_code if isinstance(exc, HTTPException) else 500
    return render_error(request, status_code)


def server_error(request: Request, exc: Exception) -> HTMLResponse:
    """Log the full trace on the server and show only the friendly 500 page."""
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return render_error(request, 500)


def add_error_pages(application: FastAPI) -> None:
    """Register the error handlers on the application."""
    application.add_exception_handler(HTTPException, http_error)
    application.add_exception_handler(Exception, server_error)
