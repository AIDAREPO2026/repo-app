"""Accounts: router layer.

HTTP routes only. Each route parses input, calls one service function and renders a response.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.accounts.guards import LOGIN_PATH, current_login, public_route, require_login_type
from app.accounts.models import Login
from app.accounts.schemas import SignInForm
from app.accounts.service import after_sign_in_path, sign_in, sign_out
from app.core.constants import LOGIN_TYPES
from app.core.db import DbSession
from app.core.navigation import Crumb, breadcrumbs, nav_for
from app.core.sessions import VISITOR_CSRF_COOKIE, new_visitor_csrf_cookie, set_cookie
from app.core.templates import templates

router = APIRouter(tags=["accounts"])

DASHBOARD_TITLES = {
    "member": "Member dashboard",
    "admin": "Admin dashboard",
    "reviewer": "Reviewer dashboard",
    "approver": "Approver dashboard",
}


# Security.md: one message for an unknown User ID, a wrong password and a locked account.
SIGN_IN_FAILED = (
    "The User ID or password is not right, or the account is locked. "
    "Check them and try again, or wait 15 minutes."
)


def render_sign_in(request: Request, next_path: str, error: str = "", user_id: str = "") -> HTMLResponse:
    """Render the sign-in form, giving a visitor a CSRF cookie if they have none."""
    cookie_value = new_visitor_csrf_cookie(request)
    context = {
        "title": "Sign in",
        "nav": nav_for(None),
        "next": next_path,
        "error": error,
        "user_id": user_id,
    }
    response = templates.TemplateResponse(request, "accounts/sign_in.html", context)
    if cookie_value:
        set_cookie(response, VISITOR_CSRF_COOKIE, cookie_value)
    return response


@router.get(LOGIN_PATH, response_class=HTMLResponse, dependencies=[Depends(public_route)])
def sign_in_page(
    request: Request, login: Annotated[Login | None, Depends(current_login)], next: str = ""
) -> Response:
    """Show the sign-in form, or send someone already signed in on to their page."""
    if login is not None:
        return RedirectResponse(after_sign_in_path(next, login), status_code=303)
    return render_sign_in(request, next)


@router.post(LOGIN_PATH, response_class=HTMLResponse, dependencies=[Depends(public_route)])
def sign_in_submit(request: Request, db: DbSession, form: Annotated[SignInForm, Form()]) -> Response:
    """Sign in and go on, or show the form again with the one generic error."""
    response = RedirectResponse("/", status_code=303)
    login = sign_in(db, form.user_id, form.password, request, response)
    if login is None:
        return render_sign_in(request, form.next, SIGN_IN_FAILED, form.user_id)
    response.headers["location"] = after_sign_in_path(form.next, login)
    return response


@router.post("/logout")
def sign_out_submit(
    request: Request, db: DbSession, login: Annotated[Login, Depends(require_login_type(*LOGIN_TYPES))]
) -> Response:
    """End this session at once and go back to the sign-in page."""
    response = RedirectResponse(LOGIN_PATH, status_code=303)
    sign_out(db, login, request, response)
    return response


def render_dashboard(request: Request, login: Login) -> HTMLResponse:
    """Render the empty dashboard shell for the login's own type."""
    context = {
        "title": DASHBOARD_TITLES[login.login_type],
        "nav": nav_for(login.login_type),
        "breadcrumbs": breadcrumbs(login.login_type),
    }
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


@router.get("/_styleguide", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def styleguide(request: Request, login: Annotated[Login | None, Depends(current_login)]) -> HTMLResponse:
    """Show every design token and component, in light and dark, for design review (P1-UI-02).

    Open to the route registry as public, because Members and visitors must get 404, not
    the sign-in redirect or 403 the login type guard gives: the page is not advertised.
    """
    if login is None or login.login_type == "member":
        raise HTTPException(status_code=404)
    context = {
        "title": "Style guide",
        "nav": nav_for(login.login_type),
        "breadcrumbs": breadcrumbs(login.login_type, Crumb("Style guide")),
    }
    return templates.TemplateResponse(request, "styleguide.html", context)
