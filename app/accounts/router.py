"""Accounts: router layer.

HTTP routes only. Each route parses input, calls one service function and renders a response.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.accounts.guards import require_login_type
from app.accounts.models import Login
from app.core.navigation import nav_for
from app.core.templates import templates

router = APIRouter(tags=["accounts"])

DASHBOARD_TITLES = {
    "member": "Member dashboard",
    "admin": "Admin dashboard",
    "reviewer": "Reviewer dashboard",
    "approver": "Approver dashboard",
}


def render_dashboard(request: Request, login: Login) -> HTMLResponse:
    """Render the empty dashboard shell for the login's own type."""
    context = {"title": DASHBOARD_TITLES[login.login_type], "nav": nav_for(login.login_type)}
    return templates.TemplateResponse(request, "accounts/dashboard.html", context)


# One route per login type, so each declares exactly who may open it (FR-2.1).
@router.get("/dashboard/member", response_class=HTMLResponse)
def member_dashboard(
    request: Request, login: Annotated[Login, Depends(require_login_type("member"))]
) -> HTMLResponse:
    """Render the Member dashboard shell."""
    return render_dashboard(request, login)


@router.get("/dashboard/admin", response_class=HTMLResponse)
def admin_dashboard(
    request: Request, login: Annotated[Login, Depends(require_login_type("admin"))]
) -> HTMLResponse:
    """Render the Admin dashboard shell."""
    return render_dashboard(request, login)


@router.get("/dashboard/reviewer", response_class=HTMLResponse)
def reviewer_dashboard(
    request: Request, login: Annotated[Login, Depends(require_login_type("reviewer"))]
) -> HTMLResponse:
    """Render the Reviewer dashboard shell."""
    return render_dashboard(request, login)


@router.get("/dashboard/approver", response_class=HTMLResponse)
def approver_dashboard(
    request: Request, login: Annotated[Login, Depends(require_login_type("approver"))]
) -> HTMLResponse:
    """Render the Approver dashboard shell."""
    return render_dashboard(request, login)
