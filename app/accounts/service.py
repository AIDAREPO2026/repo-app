"""Accounts: service layer.

Business rules. Functions take `db` and `actor` explicitly, so every caller can see what a rule needs.
"""

from datetime import timedelta

from fastapi import Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import Login, LoginAttempt, UserSession
from app.accounts.passwords import hash_password, verify_password
from app.audit.service import Actor, record
from app.core.constants import LOCKOUT_ATTEMPTS, LOCKOUT_MINUTES
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
