"""Accounts: router layer.

HTTP routes only. Each route parses input, calls one service function and renders a response.
"""

import uuid
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.accounts.guards import LOGIN_PATH, actor_for, current_login, public_route, require_login_type
from app.accounts.models import Login
from app.accounts.schemas import (
    PersonForm,
    PrivilegedAccountForm,
    ReviewerRoleForm,
    SetPasswordForm,
    SignInForm,
)
from app.accounts.service import (
    AccountRuleError,
    after_sign_in_path,
    create_privileged_account,
    deactivate_account,
    privileged_account,
    privileged_accounts,
    reassign_account,
    send_set_password_link,
    set_password_from_link,
    set_password_link_is_usable,
    set_reviewer_role,
    sign_in,
    sign_out,
)
from app.audit.service import Actor
from app.core.constants import LOGIN_TYPES
from app.core.db import DbSession
from app.core.navigation import nav_for
from app.core.sessions import VISITOR_CSRF_COOKIE, client_ip, new_visitor_csrf_cookie, set_cookie, user_agent
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


def render_visitor_form(
    request: Request, template: str, context: dict[str, Any], status_code: int = 200
) -> HTMLResponse:
    """Render a form page for visitors, giving them a CSRF cookie if they have none."""
    cookie_value = new_visitor_csrf_cookie(request)
    context = {"nav": nav_for(None)} | context
    response = templates.TemplateResponse(request, template, context, status_code=status_code)
    if cookie_value:
        set_cookie(response, VISITOR_CSRF_COOKIE, cookie_value)
    return response


def render_sign_in(request: Request, next_path: str, error: str = "", user_id: str = "") -> HTMLResponse:
    """Render the sign-in form."""
    context = {"title": "Sign in", "next": next_path, "error": error, "user_id": user_id}
    return render_visitor_form(request, "accounts/sign_in.html", context)


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


ACCOUNTS_PATH = "/admin/accounts"
# Shown after a change, picked by a fixed key so the address never carries free text.
DONE_MESSAGES = {
    "created": "Account created. A set-password link has been emailed to the person.",
    "deactivated": "Account deactivated. Its sessions have ended.",
    "reassigned": "Account reassigned. A set-password link has been emailed to the replacement.",
    "reviewer_role": "Reviewer roles updated.",
    "link_sent": "A new set-password link has been emailed.",
}
AdminLogin = Annotated[Login, Depends(require_login_type("admin"))]


def render_accounts(
    request: Request, db: Session, admin: Login, error: str = "", done: str = "", status_code: int = 200
) -> HTMLResponse:
    """Render the privileged accounts page, with an error or a done message if there is one."""
    messages = []
    if error:
        messages.append(("error", error))
    if done in DONE_MESSAGES:
        messages.append(("info", DONE_MESSAGES[done]))
    context = {
        "title": "Accounts",
        "nav": nav_for("admin"),
        "accounts": privileged_accounts(db),
        "admin_id": admin.id,
        "messages": messages,
    }
    return templates.TemplateResponse(
        request, "accounts/admin_accounts.html", context, status_code=status_code
    )


def run_account_change(
    request: Request, db: Session, admin: Login, change: Callable[[Actor], object], done: str
) -> Response:
    """Make one account change and go back to the list, or show the list with the rule it broke.

    A broken rule rolls back everything the change did, such as the deactivation half of a
    reassign whose replacement was refused.
    """
    try:
        change(actor_for(request, admin))
    except AccountRuleError as error:
        db.rollback()
        return render_accounts(request, db, admin, error=str(error), status_code=400)
    return RedirectResponse(f"{ACCOUNTS_PATH}?done={done}", status_code=303)


def account_or_404(db: Session, login_id: uuid.UUID) -> Login:
    """Return an Admin, Reviewer or Approver account, or answer 404."""
    login = privileged_account(db, login_id)
    if login is None:
        raise HTTPException(status_code=404)
    return login


def base_url(request: Request) -> str:
    """Return this site's address, for links in emails."""
    return str(request.base_url)


@router.get(ACCOUNTS_PATH, response_class=HTMLResponse)
def accounts_page(request: Request, db: DbSession, admin: AdminLogin, done: str = "") -> HTMLResponse:
    """List the Admin, Reviewer and Approver accounts, with the form to add one (FR-2.7)."""
    return render_accounts(request, db, admin, done=done)


@router.post(ACCOUNTS_PATH)
def create_account(
    request: Request, db: DbSession, admin: AdminLogin, form: Annotated[PrivilegedAccountForm, Form()]
) -> Response:
    """Create a named Admin, Reviewer or Approver account."""

    def change(actor: Actor) -> None:
        create_privileged_account(db, actor, form, base_url(request))

    return run_account_change(request, db, admin, change, "created")


@router.post(ACCOUNTS_PATH + "/{login_id}/deactivate")
def deactivate(request: Request, db: DbSession, admin: AdminLogin, login_id: uuid.UUID) -> Response:
    """Deactivate an account and end its sessions."""
    target = account_or_404(db, login_id)

    def change(actor: Actor) -> None:
        deactivate_account(db, actor, admin, target)

    return run_account_change(request, db, admin, change, "deactivated")


@router.post(ACCOUNTS_PATH + "/{login_id}/reassign")
def reassign(
    request: Request,
    db: DbSession,
    admin: AdminLogin,
    login_id: uuid.UUID,
    person: Annotated[PersonForm, Form()],
) -> Response:
    """Replace one person's account with a new person in the same role."""
    old = account_or_404(db, login_id)

    def change(actor: Actor) -> None:
        reassign_account(db, actor, admin, old, person, base_url(request))

    return run_account_change(request, db, admin, change, "reassigned")


@router.post(ACCOUNTS_PATH + "/{login_id}/reviewer-role")
def reviewer_role(
    request: Request,
    db: DbSession,
    admin: AdminLogin,
    login_id: uuid.UUID,
    form: Annotated[ReviewerRoleForm, Form()],
) -> Response:
    """Make a Reviewer the primary or the alternate."""
    reviewer = account_or_404(db, login_id)

    def change(actor: Actor) -> None:
        set_reviewer_role(db, actor, reviewer, form.is_alternate)

    return run_account_change(request, db, admin, change, "reviewer_role")


@router.post(ACCOUNTS_PATH + "/{login_id}/set-password-link")
def resend_link(request: Request, db: DbSession, admin: AdminLogin, login_id: uuid.UUID) -> Response:
    """Email a fresh set-password link, for when the first one expired."""
    target = account_or_404(db, login_id)

    def change(actor: Actor) -> None:
        send_set_password_link(db, actor, target, base_url(request))

    return run_account_change(request, db, admin, change, "link_sent")


def render_set_password(
    request: Request, token: str, usable: bool, problems: list[str] | None = None, status_code: int = 200
) -> HTMLResponse:
    """Render the set-password form, or the message for a link that cannot be used."""
    context = {"title": "Set your password", "token": token, "usable": usable, "problems": problems or []}
    return render_visitor_form(request, "accounts/set_password.html", context, status_code)


@router.get("/set-password/{token}", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def set_password_page(request: Request, db: DbSession, token: str) -> HTMLResponse:
    """Show the set-password form for a link from a new-account email."""
    usable = set_password_link_is_usable(db, token)
    return render_set_password(request, token, usable, status_code=200 if usable else 400)


@router.post("/set-password/{token}", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def set_password_submit(
    request: Request, db: DbSession, token: str, form: Annotated[SetPasswordForm, Form()]
) -> Response:
    """Set the password once, then send the person to sign in."""
    actor = Actor(kind="anonymous", ip=client_ip(request), user_agent=user_agent(request))
    try:
        problems = set_password_from_link(db, token, form.password, form.confirm_password, actor)
    except AccountRuleError:
        return render_set_password(request, token, usable=False, status_code=400)
    if problems:
        return render_set_password(request, token, usable=True, problems=problems, status_code=400)
    return RedirectResponse(LOGIN_PATH, status_code=303)
