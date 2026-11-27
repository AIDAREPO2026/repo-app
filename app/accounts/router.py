"""Accounts: router layer.

HTTP routes only. Each route parses input, calls one service function and renders a response.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app.core.constants import LOGIN_TYPES
from app.core.navigation import nav_for
from app.core.templates import templates

router = APIRouter(tags=["accounts"])

DASHBOARD_TITLES = {
    "member": "Member dashboard",
    "admin": "Admin dashboard",
    "reviewer": "Reviewer dashboard",
    "approver": "Approver dashboard",
}


# ponytail: open to anyone until P1-ACC-08 adds require_login_type(); the shells hold no data yet.
@router.get("/dashboard/{login_type}", response_class=HTMLResponse)
def dashboard(request: Request, login_type: str) -> HTMLResponse:
    """Render the empty dashboard shell for one login type."""
    if login_type not in LOGIN_TYPES:
        raise HTTPException(status_code=404)
    context = {"title": DASHBOARD_TITLES[login_type], "nav": nav_for(login_type)}
    return templates.TemplateResponse(request, "accounts/dashboard.html", context)
