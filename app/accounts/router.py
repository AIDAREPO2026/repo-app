"""Accounts: router layer.

HTTP routes only. Each route parses input, calls one service function and renders a response.
"""

import uuid
from collections.abc import Callable
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from sqlalchemy.orm import Session

from app.accounts.discom_csv import DiscomCsvError, ImportRow
from app.accounts.discom_names import DISCOM_SUGGESTIONS
from app.accounts.guards import (
    LOGIN_PATH,
    MFA_PATH,
    actor_for,
    current_login,
    mfa_pending_login,
    public_route,
    require_login_type,
    visitor_actor,
)
from app.accounts.models import Login, Organisation
from app.accounts.schemas import (
    DiscomAddForm,
    DiscomForm,
    DiscomImportForm,
    MfaCodeForm,
    MfaOffForm,
    MfaSetupForm,
    NextForm,
    PersonForm,
    PrivilegedAccountForm,
    RegistrationCodeForm,
    RegistrationForm,
    RegistrationStartForm,
    ReviewerRoleForm,
    SetPasswordForm,
    SignInForm,
)
from app.accounts.service import (
    WRONG_REGISTRATION_CODE,
    AccountRuleError,
    add_discom,
    admin_overview,
    after_sign_in_path,
    app_enrolment_details,
    check_registration_code,
    create_privileged_account,
    deactivate_account,
    discoms,
    edit_discom,
    finish_mfa,
    import_discoms,
    needs_mfa,
    preview_discom_import,
    privileged_account,
    privileged_accounts,
    reassign_account,
    register_member,
    registration_discoms,
    reset_mfa,
    send_email_code,
    send_registration_code,
    send_set_password_link,
    set_discom_active,
    set_password_from_link,
    set_password_link_is_usable,
    set_reviewer_role,
    sign_in,
    sign_out,
    start_app_enrolment,
    start_registration,
    suggest_user_ids,
    turn_off_member_mfa,
    turn_on_member_mfa,
    user_id_state,
    verified_registration,
)
from app.audit.service import Actor
from app.core import captcha
from app.core.constants import LOGIN_TYPES
from app.core.db import DbSession
from app.core.navigation import Crumb, breadcrumbs, nav_for
from app.core.sessions import (
    VISITOR_CSRF_COOKIE,
    clear_session_cookie,
    new_visitor_csrf_cookie,
    set_cookie,
)
from app.core.templates import templates
from app.core.time import to_ist, utc_now

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
    if needs_mfa(login):
        response.headers["location"] = mfa_page_path(form.next)
    else:
        response.headers["location"] = after_sign_in_path(form.next, login)
    return response


# FR-2.8: the second step of signing in. Marked public for the route registry, because these
# routes serve a session that is not signed in yet; mfa_pending_login refuses anyone else.
MfaLogin = Annotated[Login, Depends(mfa_pending_login)]
WRONG_CODE = "That code is not right, has been used or has expired. Check it and try again."
WAIT_FOR_CODE = "A code was sent less than a minute ago. Use that one, or wait a minute and ask again."


def mfa_page_path(next_path: str, method: str = "") -> str:
    """Return the address of the code page, carrying where to go afterwards."""
    query = {key: value for key, value in (("method", method), ("next", next_path)) if value}
    if not query:
        return MFA_PATH
    return f"{MFA_PATH}?{urlencode(query)}"


def render_mfa(
    request: Request,
    login: Login,
    next_path: str,
    method: str = "",
    error: str = "",
    notice: str = "",
    status_code: int = 200,
) -> HTMLResponse:
    """Render the code page, or the choice of method for a login that has no second factor yet."""
    method = login.mfa_method or method
    context = {
        "title": "Confirm it is you",
        "nav": nav_for(None),
        "next": next_path,
        "method": method,
        "enrolling": login.mfa_method is None,
        "app_setup": app_enrolment_details(login) if method == "totp" else None,
        "error": error,
        "messages": [("info", notice)] if notice else [],
    }
    return templates.TemplateResponse(request, "accounts/mfa.html", context, status_code=status_code)


@router.get(MFA_PATH, response_class=HTMLResponse, dependencies=[Depends(public_route)])
def mfa_page(
    request: Request, db: DbSession, pending: MfaLogin, next: str = "", method: str = ""
) -> HTMLResponse:
    """Ask for the second factor, or for a method to enrol."""
    if method not in ("totp", "email"):
        method = ""
    return render_mfa(request, db.get_one(Login, pending.id), next, method)


@router.post(MFA_PATH + "/setup", dependencies=[Depends(public_route)])
def mfa_setup(
    request: Request, db: DbSession, pending: MfaLogin, form: Annotated[MfaSetupForm, Form()]
) -> Response:
    """Start enrolling the chosen method: a new authenticator secret, or an emailed code."""
    login = db.get_one(Login, pending.id)
    if login.mfa_method is not None:
        return RedirectResponse(mfa_page_path(form.next), status_code=303)
    if form.method == "totp":
        start_app_enrolment(db, login)
    else:
        send_email_code(db, login)
    return RedirectResponse(mfa_page_path(form.next, form.method), status_code=303)


@router.post(MFA_PATH + "/send-code", dependencies=[Depends(public_route)])
def mfa_send_code(
    request: Request, db: DbSession, pending: MfaLogin, form: Annotated[NextForm, Form()]
) -> Response:
    """Email a new code, replacing the last one, or ask the person to wait a minute."""
    login = db.get_one(Login, pending.id)
    if login.mfa_method not in (None, "email"):
        return RedirectResponse(mfa_page_path(form.next), status_code=303)
    if not send_email_code(db, login):
        return render_mfa(request, login, form.next, "email", notice=WAIT_FOR_CODE, status_code=429)
    return RedirectResponse(mfa_page_path(form.next, "email"), status_code=303)


@router.post(MFA_PATH, response_class=HTMLResponse, dependencies=[Depends(public_route)])
def mfa_submit(
    request: Request, db: DbSession, pending: MfaLogin, form: Annotated[MfaCodeForm, Form()]
) -> Response:
    """Check the code and finish signing in, or ask again."""
    login = db.get_one(Login, pending.id)
    response = RedirectResponse(after_sign_in_path(form.next, login), status_code=303)
    result = finish_mfa(db, login, form.method, form.code, request, response)
    if result == "ok":
        return response
    if result == "locked":
        locked_out = RedirectResponse(LOGIN_PATH, status_code=303)
        clear_session_cookie(locked_out)
        return locked_out
    return render_mfa(request, login, form.next, form.method, WRONG_CODE, status_code=400)


@router.post(MFA_PATH + "/cancel", dependencies=[Depends(public_route)])
def mfa_cancel(request: Request, db: DbSession, pending: MfaLogin) -> Response:
    """Give up signing in: end the half-signed-in session."""
    response = RedirectResponse(LOGIN_PATH, status_code=303)
    sign_out(db, pending, request, response)
    return response


SECURITY_PATH = "/account/security"
SECURITY_DONE = {
    "mfa_off": ("warning", "Two-step sign-in is now off for this account."),
    "code_sent": ("info", "We have emailed you a 6-digit code. It works once, for 10 minutes."),
    "wait": ("info", WAIT_FOR_CODE),
}


def render_security(
    request: Request, db: Session, signed_in: Login, done: str = "", error: str = "", status_code: int = 200
) -> HTMLResponse:
    """Render the Security page, with a message after a change or an error for the code field."""
    messages = [SECURITY_DONE[done]] if done in SECURITY_DONE else []
    context = {
        "title": "Security",
        "nav": nav_for(signed_in.login_type),
        "breadcrumbs": breadcrumbs(signed_in.login_type, Crumb("Security")),
        "login": db.get_one(Login, signed_in.id),
        "messages": messages,
        "error": error,
    }
    return templates.TemplateResponse(request, "accounts/security.html", context, status_code=status_code)


@router.get(SECURITY_PATH, response_class=HTMLResponse)
def security_page(
    request: Request,
    db: DbSession,
    signed_in: Annotated[Login, Depends(require_login_type(*LOGIN_TYPES))],
    done: str = "",
) -> HTMLResponse:
    """Show whether two-step sign-in is on, with the Member's switch to turn it on or off (FR-2.8)."""
    return render_security(request, db, signed_in, done)


MemberLogin = Annotated[Login, Depends(require_login_type("member"))]


@router.post(SECURITY_PATH + "/mfa-on")
def member_mfa_on(request: Request, db: DbSession, member: MemberLogin) -> Response:
    """Send the Member to choose and confirm a second factor."""
    try:
        turn_on_member_mfa(db, member, request)
    except AccountRuleError:
        return RedirectResponse(SECURITY_PATH, status_code=303)
    return RedirectResponse(mfa_page_path(SECURITY_PATH), status_code=303)


@router.post(SECURITY_PATH + "/send-code")
def member_send_code(request: Request, db: DbSession, member: MemberLogin) -> Response:
    """Email a code to a Member who uses email codes, so they can turn two-step sign-in off."""
    login = db.get_one(Login, member.id)
    if login.mfa_method != "email":
        return RedirectResponse(SECURITY_PATH, status_code=303)
    done = "code_sent" if send_email_code(db, login) else "wait"
    return RedirectResponse(f"{SECURITY_PATH}?done={done}", status_code=303)


@router.post(SECURITY_PATH + "/mfa-off", response_class=HTMLResponse)
def member_mfa_off(
    request: Request, db: DbSession, member: MemberLogin, form: Annotated[MfaOffForm, Form()]
) -> Response:
    """Turn the Member's second factor off, once they give a current code."""
    try:
        result = turn_off_member_mfa(db, member, form.code, request)
    except AccountRuleError:
        return RedirectResponse(SECURITY_PATH, status_code=303)
    if result == "ok":
        return RedirectResponse(f"{SECURITY_PATH}?done=mfa_off", status_code=303)
    if result == "locked":
        locked_out = RedirectResponse(LOGIN_PATH, status_code=303)
        clear_session_cookie(locked_out)
        return locked_out
    return render_security(request, db, member, error=WRONG_CODE, status_code=400)


@router.post("/logout")
def sign_out_submit(
    request: Request, db: DbSession, login: Annotated[Login, Depends(require_login_type(*LOGIN_TYPES))]
) -> Response:
    """End this session at once and go back to the sign-in page."""
    response = RedirectResponse(LOGIN_PATH, status_code=303)
    sign_out(db, login, request, response)
    return response


def render_dashboard(request: Request, login: Login, overview: dict[str, int] | None = None) -> HTMLResponse:
    """Render the dashboard for the login's own type, with the Admin's figures when given."""
    context = {
        "title": DASHBOARD_TITLES[login.login_type],
        "nav": nav_for(login.login_type),
        "breadcrumbs": breadcrumbs(login.login_type),
        "today": to_ist(utc_now()),
        "overview": overview,
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
    request: Request, db: DbSession, login: Annotated[Login, Depends(require_login_type("admin"))]
) -> HTMLResponse:
    """Render the Admin dashboard, with the figures an Admin acts on."""
    return render_dashboard(request, login, admin_overview(db))


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
# Changes that take access away show amber, so they never look like an ordinary success.
CAUTION_DONE = {"deactivated", "mfa_reset"}


def done_message(done: str, texts: dict[str, str]) -> list[tuple[str, str]]:
    """Return the notice for a finished change, or nothing for a key that is not known."""
    if done not in texts:
        return []
    tone = "warning" if done in CAUTION_DONE else "success"
    return [(tone, texts[done])]


# Shown after a change, picked by a fixed key so the address never carries free text.
DONE_MESSAGES = {
    "created": "Account created. A set-password link has been emailed to the person.",
    "deactivated": "Account deactivated. Its sessions have ended.",
    "reassigned": "Account reassigned. A set-password link has been emailed to the replacement.",
    "reviewer_role": "Reviewer roles updated.",
    "link_sent": "A new set-password link has been emailed.",
    "mfa_reset": "MFA reset. The person sets it up again at their next sign-in.",
}
AdminLogin = Annotated[Login, Depends(require_login_type("admin"))]


def render_accounts(
    request: Request, db: Session, admin: Login, error: str = "", done: str = "", status_code: int = 200
) -> HTMLResponse:
    """Render the privileged accounts page, with an error or a done message if there is one."""
    messages = []
    if error:
        messages.append(("error", error))
    messages += done_message(done, DONE_MESSAGES)
    context = {
        "title": "Accounts",
        "nav": nav_for("admin"),
        "breadcrumbs": breadcrumbs("admin", Crumb("Accounts")),
        "accounts": privileged_accounts(db),
        "admin_id": admin.id,
        "messages": messages,
    }
    return templates.TemplateResponse(
        request, "accounts/admin_accounts.html", context, status_code=status_code
    )


# Renders an Admin list page with an error: render_accounts or render_discoms.
ListPage = Callable[..., HTMLResponse]


def run_admin_change(
    request: Request,
    db: Session,
    admin: Login,
    change: Callable[[Actor], object],
    done_url: str,
    list_page: ListPage,
) -> Response:
    """Make one Admin change and go on to done_url, or show the list page with the rule it broke.

    A broken rule rolls back everything the change did, such as the deactivation half of a
    reassign whose replacement was refused.
    """
    try:
        change(actor_for(request, admin))
    except AccountRuleError as error:
        db.rollback()
        return list_page(request, db, admin, error=str(error), status_code=400)
    return RedirectResponse(done_url, status_code=303)


def run_account_change(
    request: Request, db: Session, admin: Login, change: Callable[[Actor], object], done: str
) -> Response:
    """Make one account change and go back to the Accounts list."""
    return run_admin_change(request, db, admin, change, f"{ACCOUNTS_PATH}?done={done}", render_accounts)


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


@router.post(ACCOUNTS_PATH + "/{login_id}/reset-mfa")
def reset_account_mfa(request: Request, db: DbSession, admin: AdminLogin, login_id: uuid.UUID) -> Response:
    """Remove someone's second factor, for a lost phone, so they enrol again (FR-2.8)."""
    target = account_or_404(db, login_id)

    def change(actor: Actor) -> None:
        reset_mfa(db, actor, admin, target)

    return run_account_change(request, db, admin, change, "mfa_reset")


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
    actor = visitor_actor(request)
    try:
        problems = set_password_from_link(db, token, form.password, form.confirm_password, actor)
    except AccountRuleError:
        return render_set_password(request, token, usable=False, status_code=400)
    if problems:
        return render_set_password(request, token, usable=True, problems=problems, status_code=400)
    return RedirectResponse(LOGIN_PATH, status_code=303)


# FR-1.1, FR-1.2: a Discom asks for its Member login in three public steps: Discom and email
# (CAPTCHA protected), the emailed code, then the User ID and password.
REGISTER_PATH = "/register"
# Holds the visitor's token between steps. It is not a session: it only names what they asked.
REGISTER_COOKIE = "drr_register"


def render_registration(
    request: Request,
    db: Session,
    form: RegistrationStartForm | None = None,
    errors: dict[str, str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render step 1, with the visitor's answers and problems when sent back."""
    context = {
        "title": "Register your Discom",
        "discoms": registration_discoms(db),
        "form": form or RegistrationStartForm(),
        "errors": errors or {},
    }
    return render_visitor_form(request, "accounts/register.html", context, status_code)


def render_registration_code(request: Request, error: str = "", status_code: int = 200) -> HTMLResponse:
    """Render step 2, the same for every address, so it never says whether a code was sent."""
    context = {"title": "Enter your code", "error": error}
    return render_visitor_form(request, "accounts/register_code.html", context, status_code)


def render_registration_account(
    request: Request,
    db: Session,
    verified: tuple[Organisation, str],
    form: RegistrationForm | None = None,
    errors: dict[str, str] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render step 3 for a visitor who has proved their email."""
    discom, email = verified
    context = {
        "title": "Choose your User ID",
        "discom": discom,
        "email": email,
        "suggestions": suggest_user_ids(db, discom.name, email),
        "form": form or RegistrationForm(),
        "errors": errors or {},
    }
    return render_visitor_form(request, "accounts/register_account.html", context, status_code)


def _registration_token(request: Request) -> str:
    return request.cookies.get(REGISTER_COOKIE, "")


@router.get(REGISTER_PATH, response_class=HTMLResponse, dependencies=[Depends(public_route)])
def register_page(request: Request, db: DbSession) -> HTMLResponse:
    """Show step 1."""
    return render_registration(request, db)


@router.post(REGISTER_PATH, response_class=HTMLResponse, dependencies=[Depends(public_route)])
def register_start(
    request: Request,
    db: DbSession,
    background: BackgroundTasks,
    form: Annotated[RegistrationStartForm, Form()],
) -> Response:
    """Check the CAPTCHA, email a code if the address may register, and show the code page."""
    state = request.app.state
    captcha_passed = captcha.verify(form.altcha, state.secret_key, state.redis)
    errors, token, code = start_registration(db, state.redis, visitor_actor(request), form, captcha_passed)
    if errors:
        return render_registration(request, db, form, errors, status_code=400)
    if code:
        background.add_task(send_registration_code, form.email, code)
    response = RedirectResponse(REGISTER_PATH + "/code", status_code=303)
    set_cookie(response, REGISTER_COOKIE, token)
    return response


@router.get(REGISTER_PATH + "/code", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def register_code_page(request: Request) -> Response:
    """Show step 2."""
    if not _registration_token(request):
        return RedirectResponse(REGISTER_PATH, status_code=303)
    return render_registration_code(request)


@router.post(REGISTER_PATH + "/code", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def register_code_submit(
    request: Request, db: DbSession, form: Annotated[RegistrationCodeForm, Form()]
) -> Response:
    """Check the emailed code and let the visitor choose their login."""
    redis = request.app.state.redis
    verified = check_registration_code(
        db, redis, visitor_actor(request), _registration_token(request), form.code
    )
    if verified is None:
        return render_registration_code(request, WRONG_REGISTRATION_CODE, status_code=400)
    response = RedirectResponse(REGISTER_PATH + "/account", status_code=303)
    set_cookie(response, REGISTER_COOKIE, verified)
    return response


@router.get(REGISTER_PATH + "/account", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def register_account_page(request: Request, db: DbSession) -> Response:
    """Show step 3 to a verified visitor."""
    verified = verified_registration(db, request.app.state.redis, _registration_token(request))
    if verified is None:
        return RedirectResponse(REGISTER_PATH, status_code=303)
    return render_registration_account(request, db, verified)


@router.get(REGISTER_PATH + "/user-id", dependencies=[Depends(public_route)])
def register_user_id_state(
    request: Request, db: DbSession, value: Annotated[str, Query(max_length=254)] = ""
) -> JSONResponse:
    """Tell a verified visitor whether a User ID is free. Anyone else gets 404."""
    redis = request.app.state.redis
    token = _registration_token(request)
    if verified_registration(db, redis, token) is None:
        raise HTTPException(status_code=404)
    state = user_id_state(db, redis, token, value.strip().lower())
    return JSONResponse({"state": state}, headers={"Cache-Control": "no-store"})


@router.post(REGISTER_PATH + "/account", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def register_account_submit(
    request: Request, db: DbSession, form: Annotated[RegistrationForm, Form()]
) -> Response:
    """Record the request, then show the "sent to ITPED" page."""
    redis = request.app.state.redis
    token = _registration_token(request)
    errors = register_member(db, redis, visitor_actor(request), token, form)
    if errors is None:
        return RedirectResponse(REGISTER_PATH, status_code=303)
    if errors:
        verified = verified_registration(db, redis, token)
        if verified is None:
            return RedirectResponse(REGISTER_PATH, status_code=303)
        return render_registration_account(request, db, verified, form, errors, status_code=400)
    response = RedirectResponse(REGISTER_PATH + "/sent", status_code=303)
    response.delete_cookie(REGISTER_COOKIE, path="/")
    return response


@router.get(REGISTER_PATH + "/sent", response_class=HTMLResponse, dependencies=[Depends(public_route)])
def registration_sent(request: Request) -> HTMLResponse:
    """Confirm the request was sent."""
    context = {"title": "Request sent", "nav": nav_for(None)}
    return templates.TemplateResponse(request, "accounts/registration_sent.html", context)


@router.get("/captcha/challenge", dependencies=[Depends(public_route)])
def captcha_challenge(request: Request) -> JSONResponse:
    """Return a new signed CAPTCHA challenge for the ALTCHA widget (decision record 0006)."""
    challenge = captcha.new_challenge(request.app.state.secret_key)
    return JSONResponse(challenge, headers={"Cache-Control": "no-store"})


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


DISCOMS_PATH = "/admin/discoms"
UNCHECKED_DISCOM = "Tick the box to confirm you have checked the name and email domain."
DISCOM_DONE_MESSAGES = {
    "added": "Discom added.",
    "edited": "Discom updated.",
    "deactivated": "Discom deactivated. Its Member login can no longer sign in.",
    "reactivated": "Discom reactivated.",
}
# The 70 Discoms are a few kilobytes; this stops a wrong file early (Q-09).
MAX_IMPORT_BYTES = 100_000


def render_discoms(
    request: Request,
    db: Session,
    admin: Login,
    error: str = "",
    done: str = "",
    added: int | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    """Render the Discom master list, with an error or a done message if there is one."""
    messages = []
    if error:
        messages.append(("error", error))
    messages += done_message(done, DISCOM_DONE_MESSAGES)
    if added is not None:
        messages.append(("success", f"Discoms added from the file: {added}."))
    listed = discoms(db)
    listed_names = {discom.name.lower() for discom in listed}
    context = {
        "title": "Discoms",
        "nav": nav_for("admin"),
        "breadcrumbs": breadcrumbs("admin", Crumb("Discoms")),
        "discoms": listed,
        # The value carries both fields to the script that fills them (static/js/shell.js).
        "suggestions": [
            (f"{name}|{domain}", name)
            for name, domain in DISCOM_SUGGESTIONS
            if name.lower() not in listed_names
        ],
        "messages": messages,
    }
    return templates.TemplateResponse(
        request, "accounts/admin_discoms.html", context, status_code=status_code
    )


def run_discom_change(
    request: Request, db: Session, admin: Login, change: Callable[[Actor], object], done: str
) -> Response:
    """Make one Discom change and go back to the list."""
    return run_admin_change(request, db, admin, change, f"{DISCOMS_PATH}?done={done}", render_discoms)


def discom_or_404(db: Session, discom_id: uuid.UUID) -> Organisation:
    """Return a Discom, or answer 404."""
    discom = db.get(Organisation, discom_id)
    if discom is None:
        raise HTTPException(status_code=404)
    return discom


@router.get(DISCOMS_PATH, response_class=HTMLResponse)
def discoms_page(
    request: Request, db: DbSession, admin: AdminLogin, done: str = "", added: int | None = None
) -> HTMLResponse:
    """List the recognised Discoms, with forms to add, edit, deactivate and import them (FR-1.6)."""
    return render_discoms(request, db, admin, done=done, added=added)


@router.post(DISCOMS_PATH)
def discom_add(
    request: Request, db: DbSession, admin: AdminLogin, form: Annotated[DiscomAddForm, Form()]
) -> Response:
    """Add a Discom."""

    def change(actor: Actor) -> None:
        # D-11: the domain decides who may register, so the Admin confirms it was checked.
        if not form.checked:
            raise AccountRuleError(UNCHECKED_DISCOM)
        add_discom(db, actor, form)

    return run_discom_change(request, db, admin, change, "added")


@router.post(DISCOMS_PATH + "/{discom_id}/edit")
def discom_edit(
    request: Request,
    db: DbSession,
    admin: AdminLogin,
    discom_id: uuid.UUID,
    form: Annotated[DiscomForm, Form()],
) -> Response:
    """Change a Discom's name or email domain."""
    discom = discom_or_404(db, discom_id)

    def change(actor: Actor) -> None:
        edit_discom(db, actor, discom, form)

    return run_discom_change(request, db, admin, change, "edited")


@router.post(DISCOMS_PATH + "/{discom_id}/deactivate")
def discom_deactivate(request: Request, db: DbSession, admin: AdminLogin, discom_id: uuid.UUID) -> Response:
    """Deactivate a Discom, so it cannot register and its Member cannot sign in."""
    discom = discom_or_404(db, discom_id)

    def change(actor: Actor) -> None:
        set_discom_active(db, actor, discom, active=False)

    return run_discom_change(request, db, admin, change, "deactivated")


@router.post(DISCOMS_PATH + "/{discom_id}/reactivate")
def discom_reactivate(request: Request, db: DbSession, admin: AdminLogin, discom_id: uuid.UUID) -> Response:
    """Make a deactivated Discom active again."""
    discom = discom_or_404(db, discom_id)

    def change(actor: Actor) -> None:
        set_discom_active(db, actor, discom, active=True)

    return run_discom_change(request, db, admin, change, "reactivated")


def render_import_preview(request: Request, csv_text: str, rows: list[ImportRow]) -> HTMLResponse:
    """Render what an import would do, row by row, before anything is saved."""
    context = {
        "title": "Check the import",
        "nav": nav_for("admin"),
        "breadcrumbs": breadcrumbs("admin", Crumb("Discoms", DISCOMS_PATH), Crumb("Check the import")),
        "csv_text": csv_text,
        "rows": rows,
        "to_add": sum(1 for row in rows if row.will_be_added),
    }
    return templates.TemplateResponse(request, "accounts/discom_import.html", context)


@router.post(DISCOMS_PATH + "/import/preview", response_class=HTMLResponse)
def discom_import_preview(
    request: Request, db: DbSession, admin: AdminLogin, file: Annotated[UploadFile, File()]
) -> HTMLResponse:
    """Show what importing a CSV of Discoms would do. Nothing is saved yet."""
    content = file.file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        return render_discoms(request, db, admin, error="The file is larger than 100 KB.", status_code=400)
    try:
        csv_text = content.decode("utf-8-sig")
        rows = preview_discom_import(db, csv_text)
    except UnicodeDecodeError:
        return render_discoms(
            request, db, admin, error="Save the file as CSV UTF-8 and try again.", status_code=400
        )
    except DiscomCsvError as error:
        return render_discoms(request, db, admin, error=str(error), status_code=400)
    return render_import_preview(request, csv_text, rows)


@router.post(DISCOMS_PATH + "/import")
def discom_import(
    request: Request, db: DbSession, admin: AdminLogin, form: Annotated[DiscomImportForm, Form()]
) -> Response:
    """Add the new, problem-free rows shown in the preview."""
    try:
        added = import_discoms(db, actor_for(request, admin), form.csv_text)
    except DiscomCsvError as error:
        return render_discoms(request, db, admin, error=str(error), status_code=400)
    return RedirectResponse(f"{DISCOMS_PATH}?added={added}", status_code=303)
