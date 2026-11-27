"""Accounts: service layer.

Business rules. Functions take `db` and `actor` explicitly, so every caller can see what a rule needs.
"""

import uuid
from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import Login, LoginAttempt, LoginToken, UserSession
from app.accounts.passwords import check_password_policy, hash_password, verify_password
from app.accounts.schemas import PersonForm, PrivilegedAccountForm
from app.accounts.tokens import issue_link_token, mark_used, usable_token
from app.audit.service import SYSTEM, Actor, record
from app.core.constants import LINK_TOKEN_MINUTES, LOCKOUT_ATTEMPTS, LOCKOUT_MINUTES
from app.core.email import send_email
from app.core.sessions import clear_session_cookie, client_ip, end_session, start_session, user_agent
from app.core.time import utc_now

# Checked when the User ID is unknown, so an unknown ID takes as long as a wrong password
# and response times do not reveal which accounts exist (security.md authentication).
UNKNOWN_USER_HASH = hash_password("no account has this password")


def sign_in(db: Session, user_id: str, password: str, request: Request, response: Response) -> Login | None:
    """Check the User ID and password and, if they are right, start a new session on the response."""
    login = authenticate(db, user_id, password, client_ip(request), user_agent(request))
    if login is not None:
        start_session(db, login, request, response)
    return login


def sign_out(db: Session, login: Login, request: Request, response: Response) -> None:
    """End the current session at once and remove its cookie."""
    user_session = db.get_one(UserSession, request.state.session_id)
    end_session(db, user_session, login, "logout", client_ip(request))
    clear_session_cookie(response)


def after_sign_in_path(next_path: str, login: Login) -> str:
    """Return where to send a login after sign-in: the page it asked for, or its dashboard.

    Only a path on this site is followed, never a full or protocol-relative URL, so the
    sign-in page cannot be used to send people to another site.
    """
    is_local_path = next_path.startswith("/") and not next_path.startswith(("//", "/\\"))
    if is_local_path:
        return next_path
    return f"/dashboard/{login.login_type}"


def authenticate(db: Session, user_id: str, password: str, ip: str, user_agent: str) -> Login | None:
    """Return the login if the User ID and password are right and it may sign in, else None.

    Every outcome is logged in login_attempt. The caller shows one message for every
    None, so a visitor cannot tell an unknown User ID from a wrong password or a lockout.
    """
    attempted = user_id.strip().lower()
    login = _lock_login(db, attempted)
    if login is None:
        verify_password(UNKNOWN_USER_HASH, password)
        _log_attempt(db, attempted, None, ip, user_agent, "unknown_user")
        return None
    if is_locked(login):
        _log_attempt(db, attempted, login, ip, user_agent, "locked")
        return None
    if login.status != "active":
        _log_attempt(db, attempted, login, ip, user_agent, "inactive")
        return None
    kept_hash = _check_password(login, password)
    if kept_hash is None:
        record_failed_attempt(db, login, ip, user_agent)
        return None
    login.password_hash = kept_hash
    record_success(db, login, ip, user_agent)
    return login


def is_locked(login: Login) -> bool:
    """Return True while the login's lockout has not yet ended."""
    return login.locked_until is not None and login.locked_until > utc_now()


def record_failed_attempt(db: Session, login: Login, ip: str, user_agent: str) -> None:
    """Count a wrong password, and lock the login for 15 minutes on the 5th in a row (FR-1.7).

    The caller must hold the row lock on the login (see _lock_login), so parallel
    attempts are counted one after another and cannot get around the limit.
    """
    _log_attempt(db, login.user_id, login, ip, user_agent, "bad_password")
    login.failed_count += 1
    if login.failed_count < LOCKOUT_ATTEMPTS:
        return
    login.locked_until = utc_now() + timedelta(minutes=LOCKOUT_MINUTES)
    # The count starts again, so the next 5 failures after the lockout lock it again.
    login.failed_count = 0
    actor = Actor(kind="anonymous", ip=ip, user_agent=user_agent)
    details = {"attempts": LOCKOUT_ATTEMPTS, "minutes": LOCKOUT_MINUTES}
    record(db, actor, "accounts.lockout", "login", str(login.id), "success", details)


def record_success(db: Session, login: Login, ip: str, user_agent: str) -> None:
    """Log a successful password check and reset the failure count."""
    _log_attempt(db, login.user_id, login, ip, user_agent, "ok")
    login.failed_count = 0
    login.locked_until = None


def _check_password(login: Login, password: str) -> str | None:
    """Return the hash to keep if the password is right, or None.

    A login with no password yet (a new privileged account) never matches, but is still
    checked against a hash so it takes the same time.
    """
    if login.password_hash is None:
        verify_password(UNKNOWN_USER_HASH, password)
        return None
    return verify_password(login.password_hash, password)


def _lock_login(db: Session, user_id: str) -> Login | None:
    """Load the login for a User ID with a row lock held until the transaction ends."""
    query = select(Login).where(Login.user_id == user_id).with_for_update()
    return db.scalars(query.execution_options(populate_existing=True)).one_or_none()


def _log_attempt(
    db: Session, attempted_user_id: str, login: Login | None, ip: str, user_agent: str, reason: str
) -> None:
    """Store one sign-in attempt. The password is never stored."""
    attempt = LoginAttempt(
        attempted_user_id=attempted_user_id[:254],
        login_id=login.id if login else None,
        ip=ip,
        user_agent=user_agent[:500],
        success=reason == "ok",
        reason=reason,
    )
    db.add(attempt)
    db.flush()


class AccountRuleError(ValueError):
    """An account change that breaks a rule. The message is shown to the Admin as it is."""


LINK_NOT_USABLE = "This link has already been used or has expired. Ask an ITPED Admin to send a new one."


def privileged_accounts(db: Session) -> list[Login]:
    """Return every Admin, Reviewer and Approver account, current ones first."""
    query = (
        select(Login)
        .where(Login.login_type != "member")
        .order_by(Login.status != "active", Login.login_type, Login.is_alternate, Login.full_name)
    )
    return list(db.scalars(query))


def privileged_account(db: Session, login_id: uuid.UUID) -> Login | None:
    """Return one Admin, Reviewer or Approver account, or None, including for a Member's ID."""
    login = db.get(Login, login_id)
    if login is None or login.login_type == "member":
        return None
    return login


def create_privileged_account(db: Session, actor: Actor, form: PrivilegedAccountForm, base_url: str) -> Login:
    """Create a named Admin, Reviewer or Approver and email them a set-password link (FR-2.7).

    The account is active at once but has no password, so it cannot sign in until the
    person sets one through the link.
    """
    login = _add_privileged_login(db, form, password_hash=None)
    details = {"login_type": login.login_type, "is_alternate": login.is_alternate}
    record(db, actor, "accounts.create", "login", str(login.id), "success", details)
    send_set_password_link(db, actor, login, base_url)
    return login


def send_set_password_link(db: Session, actor: Actor, login: Login, base_url: str) -> None:
    """Email a new single-use, 60-minute set-password link to an account that has no password yet."""
    if login.status != "active" or login.password_hash is not None:
        raise AccountRuleError("Only an active account that has not set its password can get a link.")
    token = issue_link_token(db, login, "set_password")
    record(db, actor, "accounts.set_password_link", "login", str(login.id), "success")
    context = {
        "full_name": login.full_name,
        "user_id": login.user_id,
        "link": f"{base_url.rstrip('/')}/set-password/{token}",
        "minutes": LINK_TOKEN_MINUTES,
    }
    # Sent last, so nothing after it can fail and leave the person with a dead link.
    send_email(login.email, "Set your AIDA portal password", "email/set_password.txt", context)


def deactivate_account(db: Session, actor: Actor, admin: Login, target: Login) -> None:
    """Deactivate an Admin, Reviewer or Approver and end all their sessions at once (FR-2.7)."""
    if target.id == admin.id:
        raise AccountRuleError("You cannot deactivate your own account. Ask another Admin.")
    if target.status != "active":
        raise AccountRuleError("This account is not active.")
    target.status = "deactivated"
    target.updated_at = utc_now()
    db.flush()
    end_all_sessions(db, target, actor.ip)
    record(db, actor, "accounts.deactivate", "login", str(target.id), "success")


def end_all_sessions(db: Session, login: Login, ip: str | None) -> None:
    """End every open session of a login, so its cookies stop working on the next request."""
    query = select(UserSession).where(UserSession.login_id == login.id, UserSession.ended_at.is_(None))
    for user_session in db.scalars(query):
        end_session(db, user_session, login, "admin", ip)


def reassign_account(
    db: Session, actor: Actor, admin: Login, old: Login, person: PersonForm, base_url: str
) -> Login:
    """Deactivate one person's account and create their replacement in the same role (FR-2.7).

    Open review assignments move to the replacement once items can be assigned (P2-WF-02).
    """
    deactivate_account(db, actor, admin, old)
    same_role = {"login_type": old.login_type, "is_alternate": old.is_alternate}
    form = PrivilegedAccountForm.model_validate(person.model_dump() | same_role)
    new = create_privileged_account(db, actor, form, base_url)
    details = {"replaced_by": str(new.id)}
    record(db, actor, "accounts.reassign", "login", str(old.id), "success", details)
    return new


def set_reviewer_role(db: Session, actor: Actor, reviewer: Login, is_alternate: bool) -> None:
    """Make an active Reviewer the primary or the alternate, swapping with whoever holds that role."""
    if reviewer.login_type != "reviewer" or reviewer.status != "active":
        raise AccountRuleError("Only an active Reviewer can be made primary or alternate.")
    if reviewer.is_alternate == is_alternate:
        return
    holder = _active_reviewer(db, is_alternate)
    if holder is not None:
        holder.is_alternate = reviewer.is_alternate
    reviewer.is_alternate = is_alternate
    db.flush()
    details = {"is_alternate": is_alternate, "swapped_with": str(holder.id) if holder else None}
    record(db, actor, "accounts.reviewer_role", "login", str(reviewer.id), "success", details)


def set_password_link_is_usable(db: Session, token: str) -> bool:
    """Return True when a set-password link can still be used, without using it."""
    return _login_for_set_password(db, token) is not None


def set_password_from_link(
    db: Session, token: str, password: str, confirm_password: str, actor: Actor
) -> list[str]:
    """Set a new account's password through its link, once. Returns problems; empty means done.

    Raises AccountRuleError when the link is used, expired or unknown.
    """
    found = _login_for_set_password(db, token)
    if found is None:
        raise AccountRuleError(LINK_NOT_USABLE)
    login_token, login = found
    problems = check_password_policy(password, login.user_id)
    if password != confirm_password:
        problems.append("The two passwords do not match.")
    if problems:
        return problems
    login.password_hash = hash_password(password)
    login.updated_at = utc_now()
    mark_used(login_token)
    acting = Actor(kind=login.login_type, login_id=login.id, ip=actor.ip, user_agent=actor.user_agent)
    record(db, acting, "accounts.password_set", "login", str(login.id), "success")
    return []


def create_first_admin(db: Session, form: PrivilegedAccountForm, password: str) -> Login:
    """Create an Admin with a password, from the server's command line (P1-ACC-09).

    For the first Admin, or to recover when no Admin can sign in. Only someone with
    shell access to the server can run it, and it is audited as the system.
    """
    problems = check_password_policy(password, form.user_id)
    if problems:
        raise AccountRuleError(" ".join(problems))
    login = _add_privileged_login(
        db, form.model_copy(update={"login_type": "admin"}), hash_password(password)
    )
    details = {"login_type": "admin", "via": "command_line"}
    record(db, SYSTEM, "accounts.create", "login", str(login.id), "success", details)
    return login


def _add_privileged_login(db: Session, form: PrivilegedAccountForm, password_hash: str | None) -> Login:
    """Check the rules for a new account, then add it, active, to the session."""
    _check_new_account(db, form)
    login = Login(
        user_id=form.user_id,
        email=form.email.lower(),
        login_type=form.login_type,
        full_name=form.full_name.strip(),
        is_alternate=form.login_type == "reviewer" and form.is_alternate,
        password_hash=password_hash,
        status="active",
    )
    db.add(login)
    db.flush()
    return login


def _check_new_account(db: Session, form: PrivilegedAccountForm) -> None:
    """Refuse a new account that breaks a rule, with a message the Admin can act on.

    The database has the same rules as constraints, in case two Admins act at once.
    """
    problem = _new_account_problem(db, form)
    if problem:
        raise AccountRuleError(problem)


def _new_account_problem(db: Session, form: PrivilegedAccountForm) -> str | None:
    """Return why a new privileged account is not allowed, or None."""
    if db.scalar(select(Login.id).where(Login.user_id == form.user_id)) is not None:
        return "That User ID is already in use. Choose another."
    if _current_email_taken(db, form.email):
        return "Another current account uses that email. Each person needs their own (FR-2.7)."
    if form.login_type == "approver" and _active_approver(db) is not None:
        return "There is already an active Approver. Use Reassign to replace them."
    if form.login_type == "reviewer" and _active_reviewer(db, form.is_alternate) is not None:
        role = "alternate" if form.is_alternate else "primary"
        return f"There is already an active {role} Reviewer. Use Reassign to replace them."
    return None


def _current_email_taken(db: Session, email: str) -> bool:
    """Return True when a pending or active login already has this email, in any letter case."""
    query = select(Login.id).where(
        func.lower(Login.email) == email.lower(), Login.status.in_(("pending", "active"))
    )
    return db.scalar(query) is not None


def _active_approver(db: Session) -> Login | None:
    """Return the one active Approver, if there is one."""
    query = select(Login).where(Login.login_type == "approver", Login.status == "active")
    return db.scalars(query).one_or_none()


def _active_reviewer(db: Session, is_alternate: bool) -> Login | None:
    """Return the active primary or alternate Reviewer, if there is one."""
    query = select(Login).where(
        Login.login_type == "reviewer", Login.status == "active", Login.is_alternate == is_alternate
    )
    return db.scalars(query).one_or_none()


def _login_for_set_password(db: Session, token: str) -> tuple[LoginToken, Login] | None:
    """Return a usable set-password token and its login, if the login is still active."""
    login_token = usable_token(db, token, "set_password")
    if login_token is None:
        return None
    login = db.get_one(Login, login_token.login_id)
    if login.status != "active":
        return None
    return login_token, login
