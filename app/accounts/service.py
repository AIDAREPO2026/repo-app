"""Accounts: service layer.

Business rules. Functions take `db` and `actor` explicitly, so every caller can see what a rule needs.
"""

import re
import secrets
import uuid
from datetime import timedelta

from fastapi import Request, Response
from redis import Redis
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.accounts.discom_csv import ImportRow, read_discom_csv
from app.accounts.guards import actor_for
from app.accounts.mfa import (
    decrypt_secret,
    encrypt_secret,
    matching_totp_step,
    new_totp_secret,
    provisioning_uri,
    qr_code_data_uri,
)
from app.accounts.models import Login, LoginAttempt, LoginToken, Organisation, UserSession
from app.accounts.passwords import check_password_policy, hash_password, verify_password
from app.accounts.registration_store import (
    count_user_id_check,
    forget_verified,
    may_send_code,
    remember_request,
    save_code,
    use_code,
    verified_request,
)
from app.accounts.schemas import (
    EMAIL_PATTERN,
    USER_ID_PATTERN,
    DiscomForm,
    PersonForm,
    PrivilegedAccountForm,
    RegistrationForm,
    RegistrationStartForm,
    ReservedWordForm,
)
from app.accounts.tokens import (
    issue_email_code,
    issue_link_token,
    last_email_code_at,
    last_issued_at,
    retire_tokens,
    usable_token,
    use_email_code,
)
from app.accounts.user_id_rules import CATEGORIES, is_reserved, plain_word, shape_problem, split_entry
from app.audit.service import SYSTEM, Actor, record
from app.core.constants import (
    EMAIL_CODE_DIGITS,
    EMAIL_CODE_MINUTES,
    EMAIL_CODE_RESEND_SECONDS,
    LINK_TOKEN_MINUTES,
    LOCKOUT_ATTEMPTS,
    LOCKOUT_MINUTES,
    MEMBER_MAX_SESSIONS,
    PUBLIC_EMAIL_DOMAINS,
    RESERVED_ANYWHERE_MIN,
    RESERVED_WORD_MAX,
    RESERVED_WORD_MIN,
    RESERVED_WORDS_LIMIT,
    RESET_LINK_WAIT_SECONDS,
)
from app.core.email import send_email
from app.core.sessions import (
    SESSION_COOKIE,
    clear_session_cookie,
    client_ip,
    end_session,
    hash_token,
    signed_in_sessions,
    start_session,
    user_agent,
)
from app.core.settings_store import get_setting, set_setting
from app.core.time import utc_now

# Checked when the User ID is unknown, so an unknown ID takes as long as a wrong password
# and response times do not reveal which accounts exist (security.md authentication).
UNKNOWN_USER_HASH = hash_password("no account has this password")


def sign_in(db: Session, user_id: str, password: str, request: Request, response: Response) -> Login | None:
    """Check the User ID and password and, if they are right, start a new session on the response.

    A login that needs a second factor gets a session that can reach only the code page,
    and an emailed code if that is its method (FR-2.8). Raises DeviceLimitReached when a
    Member login has no device free.
    """
    login = authenticate(db, user_id, password, client_ip(request), user_agent(request))
    if login is None:
        return None
    pending = needs_mfa(login)
    # Applied before a code is asked for too, so nobody enters one only to be refused. The
    # oldest device is ended only when the new session is really about to start.
    _apply_device_limit(db, login, request, starting=not pending)
    start_session(db, login, request, response, mfa_pending=pending)
    if pending and login.mfa_method == "email":
        send_email_code(db, login)
    return login


def _apply_device_limit(db: Session, login: Login, request: Request, starting: bool) -> None:
    """Keep a Member login on at most five devices, by the Admin's policy (FR-2.3, D-10).

    The caller holds the row lock on the login (see _lock_login), so sign-ins arriving
    together are counted one after another and cannot get past the limit.
    """
    if login.login_type != "member":
        return
    # This browser's own session is replaced by signing in again, so it takes no new place.
    own = hash_token(request.cookies.get(SESSION_COOKIE, ""))
    others = [item for item in signed_in_sessions(db, login) if item.token_hash != own]
    surplus = len(others) - MEMBER_MAX_SESSIONS + 1
    if surplus <= 0:
        return
    if get_setting(db, "sixth_session_policy") == "block":
        # A shared Member login has no session here to say who tried (SRS 2.3).
        actor = Actor(kind="anonymous", ip=client_ip(request), user_agent=user_agent(request))
        details = {"reason": "device_limit"}
        record(db, actor, "accounts.login", "login", str(login.id), "denied", details)
        raise DeviceLimitReached(DEVICE_LIMIT_REFUSED)
    if not starting:
        return
    for oldest in others[:surplus]:
        end_session(db, oldest, login, "replaced", client_ip(request))


def signed_in_devices(db: Session, login: Login) -> list[UserSession]:
    """Return the sessions this login is signed in on, oldest first."""
    return signed_in_sessions(db, login)


def set_sign_in_policy(db: Session, policy: str, actor: Actor) -> None:
    """Save what a sixth device gets; the setting change is audited (FR-2.3, D-10)."""
    set_setting(db, "sixth_session_policy", policy, actor)


def sign_out_device(db: Session, login: Login, actor: Actor, session_id: uuid.UUID) -> bool:
    """End one of this login's own sessions. Return False when it is not one of them."""
    user_session = db.get(UserSession, session_id)
    if user_session is None or user_session.login_id != login.id:
        return False
    # Already ended, such as by a second click: nothing is left to do.
    if user_session.ended_at is None:
        end_session(db, user_session, login, "logout", actor.ip, by=actor)
    return True


def sign_in_policy(db: Session) -> str:
    """Return what happens when a sixth device signs in: "block" or "end_oldest"."""
    return str(get_setting(db, "sixth_session_policy"))


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
    if login.status != "active" or _discom_inactive(login):
        _log_attempt(db, attempted, login, ip, user_agent, "inactive")
        return None
    kept_hash = _check_password(login, password)
    if kept_hash is None:
        record_failed_attempt(db, login, ip, user_agent)
        return None
    login.password_hash = kept_hash
    record_success(db, login, ip, user_agent)
    return login


def _discom_inactive(login: Login) -> bool:
    """Return True for a Member whose Discom has been deactivated (FR-1.6)."""
    return login.organisation is not None and login.organisation.status != "active"


def is_locked(login: Login) -> bool:
    """Return True while the login's lockout has not yet ended."""
    return login.locked_until is not None and login.locked_until > utc_now()


def record_failed_attempt(
    db: Session, login: Login, ip: str, user_agent: str, reason: str = "bad_password"
) -> None:
    """Count a wrong password or code, and lock the login for 15 minutes on the 5th in a row (FR-1.7).

    The caller must hold the row lock on the login (see _lock_login), so parallel
    attempts are counted one after another and cannot get around the limit.
    """
    _log_attempt(db, login.user_id, login, ip, user_agent, reason)
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


def needs_mfa(login: Login) -> bool:
    """Return True when a login must give a second factor: always for privileged logins (FR-2.8)."""
    return login.login_type != "member" or login.mfa_method is not None


def send_email_code(db: Session, login: Login) -> bool:
    """Email a new sign-in code, replacing any earlier one, unless one was sent in the last minute.

    Returns whether a code was sent. The earlier code still works while it lasts.
    """
    last_sent = last_email_code_at(db, login)
    if last_sent is not None and utc_now() - last_sent < timedelta(seconds=EMAIL_CODE_RESEND_SECONDS):
        return False
    code = issue_email_code(db, login)
    context = {"full_name": login.full_name or login.user_id, "code": code, "minutes": EMAIL_CODE_MINUTES}
    send_email(login.email, "Your AIDA portal sign-in code", "email/mfa_code.txt", context)
    return True


def start_app_enrolment(db: Session, login: Login) -> None:
    """Give a login that has no second factor yet a new authenticator secret to confirm with a code."""
    if login.mfa_method is not None:
        raise AccountRuleError("This account already has a second factor.")
    login.mfa_totp_secret = encrypt_secret(new_totp_secret())
    db.flush()


def app_enrolment_details(login: Login) -> tuple[str, str] | None:
    """Return the QR code and the key to type in, for an authenticator enrolment that has started."""
    if login.mfa_method is not None or login.mfa_totp_secret is None:
        return None
    secret = decrypt_secret(login.mfa_totp_secret)
    return qr_code_data_uri(provisioning_uri(secret, login.user_id)), secret


def finish_mfa(
    db: Session, login: Login, method: str, code: str, request: Request, response: Response
) -> str:
    """Check a second-factor code and, if it is right, swap the half-signed-in session for a full one.

    Returns "ok", "wrong", "locked" or "full" (no device free). A wrong code counts towards
    the same 15-minute lockout as a wrong password, which is what limits guessing. At
    enrolment the code also confirms the chosen method.
    """
    locked = _lock_login(db, login.user_id)
    if locked is None or locked.status != "active" or is_locked(locked):
        return "locked"
    login = locked
    method = login.mfa_method or method
    result = _check_code(db, login, method, code, request)
    if result != "ok":
        return result
    try:
        _apply_device_limit(db, login, request, starting=True)
    except DeviceLimitReached:
        return "full"
    if login.mfa_method is None:
        _enrol(db, login, method, request)
    start_session(db, login, request, response)
    return "ok"


def reset_mfa(db: Session, actor: Actor, admin: Login, target: Login) -> None:
    """Remove a login's second factor and end its sessions, so it enrols again at its next sign-in.

    An Admin cannot reset their own, so a lost phone needs a second Admin to agree (FR-2.8).
    """
    if target.id == admin.id:
        raise AccountRuleError("You cannot reset your own MFA. Ask another Admin.")
    _reset(db, actor, target)


def reset_mfa_on_server(db: Session, user_id: str) -> Login:
    """Reset a login's second factor from the server's command line, for when no other Admin can.

    Running it needs shell access and the database settings on the server, which is the
    second person's agreement that a reset through the portal would need.
    """
    target = _lock_login(db, user_id.strip().lower())
    if target is None:
        raise AccountRuleError("No login has that User ID.")
    _reset(db, SYSTEM, target, {"via": "command_line"})
    return target


def _reset(db: Session, actor: Actor, target: Login, details: dict[str, str] | None = None) -> None:
    """Clear a login's second factor, end its sessions and audit the reset."""
    _clear_mfa(target)
    db.flush()
    end_all_sessions(db, target, actor.ip)
    record(db, actor, "accounts.mfa_reset", "login", str(target.id), "success", details)


def turn_on_member_mfa(db: Session, login: Login, request: Request) -> None:
    """Send a Member's session back to the code page, where they choose and confirm a method."""
    if login.login_type != "member" or login.mfa_method is not None:
        raise AccountRuleError("MFA is already on for this account.")
    user_session = db.get_one(UserSession, request.state.session_id)
    user_session.mfa_pending = True
    db.flush()


def turn_off_member_mfa(db: Session, login: Login, code: str, request: Request) -> str:
    """Turn a Member's second factor off once they give a current code, and return "ok", "wrong" or "locked".

    The code means a session left open on someone else's computer cannot remove the
    protection. Privileged logins must keep theirs (FR-2.8).
    """
    if login.login_type != "member":
        raise AccountRuleError("MFA is required for Admin, Reviewer and Approver accounts.")
    member = _lock_login(db, login.user_id)
    if member is None or member.mfa_method is None:
        raise AccountRuleError("MFA is already off for this account.")
    result = _check_code(db, member, member.mfa_method, code, request)
    if result != "ok":
        return result
    _clear_mfa(member)
    db.flush()
    record(db, actor_for(request, member), "accounts.mfa_off", "login", str(member.id), "success")
    return "ok"


def _check_code(db: Session, login: Login, method: str, code: str, request: Request) -> str:
    """Check a code for a login held under its row lock, counting a wrong one towards the lockout."""
    if not _code_is_right(db, login, method, code.strip()):
        return _refuse_code(db, login, request)
    login.failed_count = 0
    return "ok"


def _code_is_right(db: Session, login: Login, method: str, code: str) -> bool:
    """Check a code against the login's emailed code or authenticator secret, using it up if right."""
    if method == "email":
        return use_email_code(db, login, code)
    if method != "totp" or login.mfa_totp_secret is None:
        return False
    step = matching_totp_step(decrypt_secret(login.mfa_totp_secret), code, login.mfa_totp_last_step)
    if step is None:
        return False
    login.mfa_totp_last_step = step
    return True


def _refuse_code(db: Session, login: Login, request: Request) -> str:
    """Count and audit a wrong code, and end the current session if the login is now locked."""
    ip = client_ip(request)
    record_failed_attempt(db, login, ip, user_agent(request), reason="mfa_failed")
    record(db, actor_for(request, login), "accounts.mfa", "login", str(login.id), "failure")
    if not is_locked(login):
        return "wrong"
    user_session = db.get_one(UserSession, request.state.session_id)
    end_session(db, user_session, login, "locked", ip)
    return "locked"


def _enrol(db: Session, login: Login, method: str, request: Request) -> None:
    """Record the method a login has just confirmed with its first code."""
    login.mfa_method = method
    login.mfa_enrolled_at = utc_now()
    if method == "email":
        login.mfa_totp_secret = None
    db.flush()
    record(
        db,
        actor_for(request, login),
        "accounts.mfa_enrol",
        "login",
        str(login.id),
        "success",
        {"method": method},
    )


def _clear_mfa(login: Login) -> None:
    """Remove every second-factor setting from a login."""
    login.mfa_method = None
    login.mfa_totp_secret = None
    login.mfa_totp_last_step = None
    login.mfa_enrolled_at = None
    login.updated_at = utc_now()


class AccountRuleError(ValueError):
    """An account change that breaks a rule. The message is shown to the Admin as it is."""


class DeviceLimitReached(AccountRuleError):
    """A sixth device tried to sign in to a Member login under the "block" policy."""


DEVICE_LIMIT_REFUSED = (
    f"This Discom login is already signed in on {MEMBER_MAX_SESSIONS} devices. "
    "Sign out on another device or contact ITPED."
)


PUBLIC_DOMAIN_REFUSED = (
    "Anyone can get an address on this email service. Use the domain of the Discom's own staff email."
)
LINK_NOT_USABLE = "This link has already been used or has expired."


def privileged_accounts(db: Session) -> list[Login]:
    """Return every Admin, Reviewer and Approver account, current ones first."""
    query = (
        select(Login)
        .where(Login.login_type != "member")
        .order_by(Login.status != "active", Login.login_type, Login.is_alternate, Login.full_name)
    )
    return list(db.scalars(query))


def open_roles(db: Session) -> list[str]:
    """Return the roles a new account can be given now.

    The Approver and each Reviewer seat hold one person (FR-2.7), so a filled one is not offered.
    """
    roles = ["admin"]
    if _active_reviewer(db, is_alternate=False) is None:
        roles.append("reviewer")
    if _active_reviewer(db, is_alternate=True) is None:
        roles.append("alternate_reviewer")
    if _active_approver(db) is None:
        roles.append("approver")
    return roles


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
    if shape_problem(form.user_id) or _user_id_reserved(db, form.user_id, None):
        raise AccountRuleError(USER_ID_NOT_ALLOWED)
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


def end_all_sessions(db: Session, login: Login, ip: str | None, reason: str = "admin") -> None:
    """End every open session of a login, so its cookies stop working on the next request."""
    query = select(UserSession).where(UserSession.login_id == login.id, UserSession.ended_at.is_(None))
    for user_session in db.scalars(query):
        end_session(db, user_session, login, reason, ip)


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


def link_is_usable(db: Session, token: str, purpose: str) -> bool:
    """Return True when an emailed password link can still be used, without using it."""
    return _login_for_link(db, token, purpose) is not None


def set_password_from_link(
    db: Session, token: str, password: str, confirm_password: str, actor: Actor
) -> list[str]:
    """Set a new account's password through its link, once. Returns problems; empty means done.

    Raises AccountRuleError when the link is used, expired or unknown.
    """
    login, problems = _use_password_link(db, token, "set_password", password, confirm_password)
    if not problems:
        # Only privileged accounts set a first password, so the audit can name the person.
        acting = Actor(kind=login.login_type, login_id=login.id, ip=actor.ip, user_agent=actor.user_agent)
        record(db, acting, "accounts.password_set", "login", str(login.id), "success")
    return problems


def request_password_reset(
    db: Session, actor: Actor, identifier: str, portal_url: str, captcha_passed: bool
) -> tuple[str, str, str]:
    """Take a "Forgot password" request. Returns (problem, address to email, link).

    The visitor is answered the same way whether or not an account matches, so the address and
    link are empty when nothing is to be sent. The audit records why not.
    """
    # The CAPTCHA is checked first, so bots cost us no database work (FR-1.2).
    if not captcha_passed:
        _audit_reset_request(db, actor, None, "captcha")
        return CAPTCHA_FAILED, "", ""
    if not identifier.strip():
        return "Enter your User ID or the email address of your account.", "", ""
    login = _login_for_reset(db, identifier)
    if login is None:
        _audit_reset_request(db, actor, None, "no_account")
        return "", "", ""
    last_sent = last_issued_at(db, login, "reset_password")
    if last_sent is not None and utc_now() - last_sent < timedelta(seconds=RESET_LINK_WAIT_SECONDS):
        _audit_reset_request(db, actor, login, "too_soon")
        return "", "", ""
    retire_tokens(db, login, "reset_password")
    token = issue_link_token(db, login, "reset_password")
    _audit_reset_request(db, actor, login, "")
    return "", login.email, f"{portal_url.rstrip('/')}/reset-password/{token}"


def send_password_reset_link(email: str, link: str) -> None:
    """Email the link. The route sends it after answering, so timing does not tell who got one."""
    context = {"link": link, "minutes": LINK_TOKEN_MINUTES}
    send_email(email, "Reset your AIDA portal password", "email/reset_password.txt", context)


def reset_password(db: Session, token: str, password: str, confirm_password: str, actor: Actor) -> list[str]:
    """Replace a password through a reset link, once. Returns problems; empty means done.

    Every session ends and any lockout is cleared (FR-1.5). A second factor is not touched.
    """
    login, problems = _use_password_link(db, token, "reset_password", password, confirm_password)
    if problems:
        return problems
    login.failed_count = 0
    login.locked_until = None
    db.flush()
    end_all_sessions(db, login, actor.ip, reason="password_reset")
    # Recorded as the visitor who held the link: a shared Member login has no session here to
    # say who that was (SRS 2.3).
    record(db, actor, "accounts.password_reset", "login", str(login.id), "success")
    _tell_owner_password_changed(login)
    return []


def _tell_owner_password_changed(login: Login) -> None:
    """Email the account's address, so a change its owner did not make does not go unnoticed.

    No link is included: nothing here should teach people to click one in a warning.
    """
    context = {"user_id": login.user_id, "changed_at": utc_now()}
    send_email(login.email, "Your AIDA portal password was changed", "email/password_changed.txt", context)


def _use_password_link(
    db: Session, token: str, purpose: str, password: str, confirm_password: str
) -> tuple[Login, list[str]]:
    """Save the password chosen through a link, and retire every password link of the login."""
    found = _login_for_link(db, token, purpose)
    if found is None:
        raise AccountRuleError(LINK_NOT_USABLE)
    _, login = found
    problems = _password_problems(password, confirm_password, login.user_id)
    if problems:
        return login, problems
    login.password_hash = hash_password(password)
    login.updated_at = utc_now()
    retire_tokens(db, login, "set_password", "reset_password")
    return login, []


def _password_problems(password: str, confirm_password: str, user_id: str) -> list[str]:
    """Return what is wrong with a new password typed twice (FR-1.7)."""
    problems = check_password_policy(password, user_id)
    if password != confirm_password:
        problems.append("The two passwords do not match.")
    return problems


def _audit_reset_request(db: Session, actor: Actor, login: Login | None, refusal: str) -> None:
    """Audit asking for a reset link. What the visitor typed is not kept."""
    result = "denied" if refusal else "success"
    details = {"reason": refusal} if refusal else None
    target = str(login.id) if login else None
    record(db, actor, "accounts.password_reset_request", "login", target, result, details)


def _login_for_reset(db: Session, identifier: str) -> Login | None:
    """Return the account a User ID or email names, if it may sign in, locked for this request."""
    value = identifier.strip().lower()
    # A User ID cannot hold "@", and current accounts never share an email.
    query = (
        select(Login)
        .where(or_(Login.user_id == value, func.lower(Login.email) == value), Login.status == "active")
        .with_for_update(of=Login)
    )
    login = db.scalars(query).one_or_none()
    if login is None or _discom_inactive(login):
        return None
    return login


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
    if _user_id_taken(db, form.user_id):
        return "That User ID is already in use. Choose another."
    if _current_email_taken(db, form.email):
        return "Another current account uses that email. Each person needs their own (FR-2.7)."
    if form.login_type == "approver" and _active_approver(db) is not None:
        return "There is already an active Approver. Use Reassign to replace them."
    if form.login_type == "reviewer" and _active_reviewer(db, form.is_alternate) is not None:
        role = "alternate" if form.is_alternate else "primary"
        return f"There is already an active {role} Reviewer. Use Reassign to replace them."
    return None


def _user_id_taken(db: Session, user_id: str) -> bool:
    """Return True when any login, in any state, already has this User ID."""
    return db.scalar(select(Login.id).where(Login.user_id == user_id)) is not None


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


def _login_for_link(db: Session, token: str, purpose: str) -> tuple[LoginToken, Login] | None:
    """Return a usable password link's token and login, if the account may still sign in."""
    login_token = usable_token(db, token, purpose)
    if login_token is None:
        return None
    login = db.get_one(Login, login_token.login_id)
    if login.status != "active" or _discom_inactive(login):
        return None
    return login_token, login


# P1-ACC-01: three fictional Discoms for development and staging until ITPED supplies the
# real list (Q-09). tests/fixture_data.py uses the same ones.
TEST_DISCOMS = (
    DiscomForm(name="North Test Discom", email_domain="north-discom.example"),
    DiscomForm(name="South Test Discom", email_domain="south-discom.example"),
    DiscomForm(name="East Test Discom", email_domain="east-discom.example"),
)
SEED_ENVIRONMENTS = ("local", "development", "test", "staging")


def pending_registrations(db: Session) -> list[Login]:
    """Return the Member registrations waiting for ITPED, oldest first (FR-1.3)."""
    query = (
        select(Login)
        .where(Login.login_type == "member", Login.status == "pending")
        .order_by(Login.created_at)
    )
    return list(db.scalars(query))


def approve_registration(db: Session, actor: Actor, login_id: uuid.UUID, sign_in_url: str) -> None:
    """Activate a pending Member login and tell the Discom (FR-1.4)."""
    login = _undecided_registration(db, login_id)
    if _discom_inactive(login):
        raise AccountRuleError("This Discom is deactivated. Reactivate it first, or decline the request.")
    _decide(db, actor, login, "active", "accounts.registration_approve")
    context = {"discom": _discom_name(login), "user_id": login.user_id, "link": sign_in_url}
    send_email(login.email, "Your AIDA portal login is active", "email/registration_approved.txt", context)


def decline_registration(db: Session, actor: Actor, login_id: uuid.UUID, reason: str) -> None:
    """Decline a pending registration with a reason, which frees the Discom to register again."""
    reason = reason.strip()
    if not reason:
        raise AccountRuleError("Give a reason for declining. The Discom receives it.")
    login = _undecided_registration(db, login_id)
    login.decline_reason = reason
    _decide(db, actor, login, "declined", "accounts.registration_decline", {"reason": reason})
    context = {"discom": _discom_name(login), "reason": reason}
    send_email(login.email, "Your AIDA portal registration", "email/registration_declined.txt", context)


def _undecided_registration(db: Session, login_id: uuid.UUID) -> Login:
    """Return a pending Member login, locked so two Admins cannot both decide it."""
    login = db.get(Login, login_id, with_for_update=True, populate_existing=True)
    if login is None or login.login_type != "member" or login.status != "pending":
        raise AccountRuleError("This request is not waiting for a decision. Someone may have decided it.")
    return login


def _decide(
    db: Session,
    actor: Actor,
    login: Login,
    status: str,
    action: str,
    details: dict[str, str] | None = None,
) -> None:
    """Save the decision with who made it and when, and audit it."""
    login.status = status
    login.verified_at = utc_now()
    login.verified_by = actor.login_id
    login.updated_at = login.verified_at
    db.flush()
    record(db, actor, action, "login", str(login.id), "success", details)


def _discom_name(login: Login) -> str:
    """Return the name of a Member login's Discom."""
    assert login.organisation is not None  # noqa: S101 - the database requires it for a Member
    return login.organisation.name


def admin_overview(db: Session) -> dict[str, int]:
    """Return the figures on the Admin dashboard: Discoms, waiting requests and ITPED accounts."""
    count = select(func.count()).select_from(Login)
    return {
        "active_discoms": db.scalar(
            select(func.count()).select_from(Organisation).where(Organisation.status == "active")
        )
        or 0,
        "pending_requests": db.scalar(count.where(Login.login_type == "member", Login.status == "pending"))
        or 0,
        "itped_accounts": db.scalar(count.where(Login.login_type != "member", Login.status == "active")) or 0,
    }


def discoms(db: Session) -> list[Organisation]:
    """Return every Discom, active ones first, then by name."""
    query = select(Organisation).order_by(Organisation.status != "active", func.lower(Organisation.name))
    return list(db.scalars(query))


def add_discom(db: Session, actor: Actor, form: DiscomForm, via: str = "form") -> Organisation:
    """Add a Discom to the master list, refusing a name or domain already listed (FR-1.6)."""
    _check_domain_is_not_public(form.email_domain)
    _check_discom_is_unique(db, form)
    discom = Organisation(name=form.name, email_domain=form.email_domain)
    db.add(discom)
    db.flush()
    details = {"name": discom.name, "email_domain": discom.email_domain, "via": via}
    record(db, actor, "accounts.discom_add", "organisation", str(discom.id), "success", details)
    return discom


def edit_discom(db: Session, actor: Actor, discom: Organisation, form: DiscomForm) -> None:
    """Change a Discom's name or email domain, keeping both unique."""
    _check_domain_is_not_public(form.email_domain)
    _check_discom_is_unique(db, form, discom.id)
    before = {"name": discom.name, "email_domain": discom.email_domain}
    discom.name = form.name
    discom.email_domain = form.email_domain
    discom.updated_at = utc_now()
    db.flush()
    details = {"before": before, "after": {"name": discom.name, "email_domain": discom.email_domain}}
    record(db, actor, "accounts.discom_edit", "organisation", str(discom.id), "success", details)


def set_discom_active(db: Session, actor: Actor, discom: Organisation, active: bool) -> None:
    """Deactivate or reactivate a Discom. Deactivating ends its Member's sessions at once.

    Discoms are never deleted (SRS 6.3); an inactive one cannot register or sign in.
    """
    discom.status = "active" if active else "inactive"
    discom.updated_at = utc_now()
    db.flush()
    if not active:
        for member in db.scalars(select(Login).where(Login.organisation_id == discom.id)):
            end_all_sessions(db, member, actor.ip)
    action = "accounts.discom_reactivate" if active else "accounts.discom_deactivate"
    record(db, actor, action, "organisation", str(discom.id), "success")


def preview_discom_import(db: Session, csv_text: str) -> list[ImportRow]:
    """Read a Discom CSV and say, row by row, whether it will be added, is already listed or has a problem.

    Raises DiscomCsvError when the file as a whole cannot be read.
    """
    rows = read_discom_csv(csv_text)
    for row in rows:
        if not row.problem and row.email_domain in PUBLIC_EMAIL_DOMAINS:
            row.problem = PUBLIC_DOMAIN_REFUSED
        if not row.problem:
            _compare_with_list(db, row)
    return rows


def import_discoms(db: Session, actor: Actor, csv_text: str) -> int:
    """Add the new, problem-free rows of a Discom CSV and return how many were added.

    The file is checked again here, so rows are judged against the list as it is now.
    """
    added = 0
    for row in preview_discom_import(db, csv_text):
        if row.will_be_added:
            add_discom(db, actor, DiscomForm(name=row.name, email_domain=row.email_domain), via="import")
            added += 1
    return added


def seed_test_discoms(db: Session, app_env: str) -> int:
    """Add the three fictional Discoms if they are missing, outside production only, and return how many."""
    if app_env not in SEED_ENVIRONMENTS:
        raise AccountRuleError(f"Test Discoms are only for {', '.join(SEED_ENVIRONMENTS)}, not {app_env}.")
    added = 0
    for form in TEST_DISCOMS:
        if _discom_with_domain(db, form.email_domain) is None:
            add_discom(db, SYSTEM, form, via="seed")
            added += 1
    return added


def _check_domain_is_not_public(email_domain: str) -> None:
    """Refuse a mail service anyone can join, such as gmail.com (D-11)."""
    if email_domain in PUBLIC_EMAIL_DOMAINS:
        raise AccountRuleError(PUBLIC_DOMAIN_REFUSED)


def _check_discom_is_unique(db: Session, form: DiscomForm, own_id: uuid.UUID | None = None) -> None:
    """Refuse a name or domain that another Discom already has."""
    same_name = _discom_with_name(db, form.name)
    if same_name is not None and same_name.id != own_id:
        raise AccountRuleError("A Discom with this name is already listed.")
    same_domain = _discom_with_domain(db, form.email_domain)
    if same_domain is not None and same_domain.id != own_id:
        raise AccountRuleError("A Discom with this email domain is already listed.")


def _compare_with_list(db: Session, row: ImportRow) -> None:
    """Mark an import row that matches a listed Discom exactly, or clashes with one."""
    same_domain = _discom_with_domain(db, row.email_domain)
    same_name = _discom_with_name(db, row.name)
    if same_domain is not None and same_domain is same_name:
        row.already_listed = True
    elif same_domain is not None:
        row.problem = f"This domain is already listed for {same_domain.name}."
    elif same_name is not None:
        row.problem = f"This name is already listed with the domain {same_name.email_domain}."


def _discom_with_name(db: Session, name: str) -> Organisation | None:
    """Return the Discom with this name, ignoring case."""
    query = select(Organisation).where(func.lower(Organisation.name) == name.lower())
    return db.scalars(query).one_or_none()


def _discom_with_domain(db: Session, email_domain: str) -> Organisation | None:
    """Return the Discom with this email domain."""
    return db.scalars(select(Organisation).where(Organisation.email_domain == email_domain)).one_or_none()


USER_ID_NOT_ALLOWED = "That User ID is not allowed. Choose another."
WRONG_REGISTRATION_CODE = "That code is not right or has expired. Check the email, or start again."
CAPTCHA_FAILED = (
    "The check that you are not a robot did not finish. Tick the box, wait for it, then send the form again."
)
DISCOM_TAKEN = (
    "This Discom already has a portal login or a request waiting for ITPED. Contact ITPED if you need help."
)


def start_registration(
    db: Session, redis: Redis, actor: Actor, form: RegistrationStartForm, captcha_passed: bool
) -> tuple[dict[str, str], str, str]:
    """Take step 1 of a request. Returns (problems by field, visitor token, code to email).

    With no problems the visitor gets a token and the code page, whatever the address. A code
    is returned only when the address may register this Discom, so the page cannot be used to
    learn Discom domains or who has a login (spec security). The audit records why not.
    """
    # Spec: the CAPTCHA is checked before anything else, so bots cost us no database work.
    if not captcha_passed:
        _audit_code(db, actor, "denied", {"reason": "captcha"})
        return {"altcha": CAPTCHA_FAILED}, "", ""
    problems = _start_format_problems(db, form)
    if problems:
        _audit_code(db, actor, "denied", {"reason": "format", "fields": sorted(problems)})
        return problems, "", ""
    discom = db.get_one(Organisation, uuid.UUID(form.organisation_id))
    details: dict[str, object] = {"organisation_id": str(discom.id)}
    if _discom_has_member_login(db, discom):
        _audit_code(db, actor, "denied", details | {"reason": "discom_has_login"})
        return {"organisation_id": DISCOM_TAKEN}, "", ""
    token = remember_request(redis, str(discom.id), form.email)
    refusal = _email_refusal(db, discom, form.email)
    if refusal is None and not may_send_code(redis, form.email):
        refusal = "too_soon"
    if refusal:
        _audit_code(db, actor, "denied", details | {"reason": refusal})
        return {}, token, ""
    code = f"{secrets.randbelow(10**EMAIL_CODE_DIGITS):0{EMAIL_CODE_DIGITS}d}"
    save_code(redis, str(discom.id), form.email, code)
    _audit_code(db, actor, "success", details)
    return {}, token, code


def send_registration_code(email: str, code: str) -> None:
    """Email the code. The route sends it after answering, so timing does not tell who got one."""
    context = {"code": code, "minutes": EMAIL_CODE_MINUTES}
    send_email(email, "Your AIDA portal registration code", "email/registration_code.txt", context)


def check_registration_code(db: Session, redis: Redis, actor: Actor, token: str, code: str) -> str | None:
    """Return the verified visitor's new token if the code is right, else None."""
    verified = use_code(redis, token, code)
    if verified is None:
        _audit_code(db, actor, "denied", {"reason": "wrong_code"})
    return verified


def verified_registration(db: Session, redis: Redis, token: str) -> tuple[Organisation, str] | None:
    """Return the Discom and email a visitor has proved, while the Discom can still register."""
    request = verified_request(redis, token)
    if request is None:
        return None
    discom = _active_discom(db, request["organisation_id"])
    if discom is None or _email_refusal(db, discom, request["email"]):
        return None
    return discom, request["email"]


def user_id_state(db: Session, redis: Redis, token: str, user_id: str) -> str:
    """Say whether a User ID is "free", "taken" or "invalid", or "limit" after too many asks.

    Only for a verified visitor: the caller must have checked verified_registration() first.
    """
    if not count_user_id_check(redis, token):
        return "limit"
    if not re.fullmatch(USER_ID_PATTERN, user_id) or shape_problem(user_id):
        return "invalid"
    visitor = verified_registration(db, redis, token)
    if _user_id_reserved(db, user_id, visitor[0] if visitor else None):
        return "reserved"
    return "taken" if _user_id_taken(db, user_id) else "free"


def suggest_user_ids(db: Session, discom: Organisation, email: str, wanted: int = 3) -> list[str]:
    """Return User IDs that are free and allowed now, built from the email and the Discom's name."""
    person = _user_id_part(email.partition("@")[0])
    code = _discom_code(discom.name)
    bases = [person, f"{code}.{person}" if code and person else "", f"{code}.office" if code else ""]
    # The last one always passes, so there is something to offer whatever the email says.
    bases = [base for base in bases if base] + ["nodal.office"]
    suggestions: list[str] = []
    # The plain forms first, then the same with a number, until enough are found.
    for number in ["", *range(2, 100)]:
        for base in bases:
            candidate = f"{base}{number}"
            if candidate not in suggestions and _user_id_open(db, candidate, discom):
                suggestions.append(candidate)
            if len(suggestions) == wanted:
                return suggestions
    return suggestions


def _user_id_open(db: Session, user_id: str, discom: Organisation) -> bool:
    """Return True for a User ID this Discom could take now."""
    if not re.fullmatch(USER_ID_PATTERN, user_id) or shape_problem(user_id):
        return False
    return not _user_id_reserved(db, user_id, discom) and not _user_id_taken(db, user_id)


def reserved_entries(db: Session, where: str) -> list[tuple[str, str]]:
    """Return one reserved list, "anywhere" or "parts", as (category, word)."""
    stored = get_setting(db, f"reserved_user_id_{where}")
    assert isinstance(stored, list)  # noqa: S101 - the setting's rule allows nothing else
    return [split_entry(entry) for entry in stored]


def reserved_words(db: Session, where: str) -> list[str]:
    """Return just the words of one reserved list."""
    return [word for _, word in reserved_entries(db, where)]


def reserve_word(db: Session, actor: Actor, form: ReservedWordForm) -> None:
    """Add a word nobody may use in a User ID. Existing logins are not affected."""
    word = plain_word(form.word)
    smallest = RESERVED_ANYWHERE_MIN if form.where == "anywhere" else RESERVED_WORD_MIN
    if not re.fullmatch(r"[a-z0-9]+", word) or not smallest <= len(word) <= RESERVED_WORD_MAX:
        raise AccountRuleError(f"Use {smallest} to {RESERVED_WORD_MAX} letters or numbers.")
    if form.category not in CATEGORIES:
        raise AccountRuleError("Choose a category from the list.")
    entries = reserved_entries(db, form.where)
    if word in reserved_words(db, form.where):
        raise AccountRuleError("That word is already reserved.")
    if len(entries) >= RESERVED_WORDS_LIMIT:
        raise AccountRuleError("The list is full. Remove a word first.")
    _save_reserved(db, actor, form.where, [*entries, (form.category, word)])
    _forget_removed(db, actor, form.where, word)


def free_word(db: Session, actor: Actor, form: ReservedWordForm) -> None:
    """Take a word off a reserved list."""
    entries = reserved_entries(db, form.where)
    remaining = [entry for entry in entries if entry[1] != form.word]
    if len(remaining) == len(entries):
        raise AccountRuleError("That word is not on the list.")
    _save_reserved(db, actor, form.where, remaining)
    category = next(category for category, word in entries if word == form.word)
    _forget_removed(db, actor, form.where, form.word)
    removed = [*_removed_stored(db), f"{form.where}:{category}:{form.word}"]
    set_setting(db, "reserved_user_id_removed", removed, actor)


def removed_words(db: Session) -> list[tuple[str, str, str]]:
    """Return the words taken off the lists, as (word, category, where)."""
    parts = (entry.split(":", 2) for entry in _removed_stored(db))
    return sorted((word, category, where) for where, category, word in parts)


def restore_word(db: Session, actor: Actor, form: ReservedWordForm) -> None:
    """Put a removed word back on the list it came from, with its category."""
    for word, category, where in removed_words(db):
        if word == form.word and where == form.where:
            reserve_word(db, actor, ReservedWordForm(word=word, where=where, category=category))
            return
    raise AccountRuleError("That word is not among the removed ones.")


def _removed_stored(db: Session) -> list[str]:
    stored = get_setting(db, "reserved_user_id_removed")
    assert isinstance(stored, list)  # noqa: S101 - the setting's rule allows nothing else
    return stored


def _forget_removed(db: Session, actor: Actor, where: str, word: str) -> None:
    """Drop a word from the removed ones, when it is reserved again."""
    stored = _removed_stored(db)
    kept = [entry for entry in stored if entry.split(":", 2)[::2] != [where, word]]
    if kept != stored:
        set_setting(db, "reserved_user_id_removed", kept, actor)


def _save_reserved(db: Session, actor: Actor, where: str, entries: list[tuple[str, str]]) -> None:
    """Store a list as "category:word" entries; set_setting audits the change."""
    stored = sorted((f"{category}:{word}" for category, word in entries), key=lambda e: split_entry(e)[1])
    set_setting(db, f"reserved_user_id_{where}", stored, actor)


def _user_id_reserved(db: Session, user_id: str, own: Organisation | None) -> bool:
    """Return True for a reserved word, or another Discom's code. own is the Discom asking."""
    codes = [
        plain_word(code)
        for name, discom_id in db.execute(select(Organisation.name, Organisation.id))
        if (code := _bracketed_code(name)) and (own is None or discom_id != own.id)
    ]
    own_code = plain_word(_bracketed_code(own.name)) if own else ""
    parts = reserved_words(db, "parts") + [code for code in codes if code != own_code]
    return is_reserved(user_id, reserved_words(db, "anywhere"), parts)


def _bracketed_code(name: str) -> str:
    """Return the code a Discom writes in brackets, such as MSEDCL, or ""."""
    bracketed = re.search(r"\(([A-Za-z0-9-]{2,15})\)", name)
    return bracketed.group(1) if bracketed else ""


def _user_id_part(text: str) -> str:
    """Keep only the characters a User ID may have, without dots or dashes at the ends."""
    return re.sub(r"[^a-z0-9._-]", "", text.lower()).strip("._-")


def _discom_code(name: str) -> str:
    """Return a short code for suggestions: the one in brackets, else the first word."""
    words = name.split()
    return _user_id_part(_bracketed_code(name) or (words[0] if words else ""))


def register_member(
    db: Session, redis: Redis, actor: Actor, token: str, form: RegistrationForm
) -> dict[str, str] | None:
    """Create the pending Member login for a verified visitor (FR-1.1).

    Returns problems by field, empty when the request was sent, or None when the visitor's
    verification is missing or no longer holds, so they must start again.
    """
    verified = verified_registration(db, redis, token)
    if verified is None:
        return None
    discom, email = verified
    details: dict[str, object] = {"organisation_id": str(discom.id), "user_id": form.user_id}
    if _discom_has_member_login(db, discom):
        _audit_registration(db, actor, "denied", details | {"reason": "discom_has_login"})
        return {"user_id": DISCOM_TAKEN}
    problems = _account_problems(db, form, discom)
    if problems:
        _audit_registration(db, actor, "denied", details | {"reason": "format", "fields": sorted(problems)})
        return problems
    login = _add_pending_member(db, form, discom, email)
    record(db, actor, "accounts.register", "login", str(login.id), "success", details)
    forget_verified(redis, token)
    return {}


def registration_discoms(db: Session) -> list[Organisation]:
    """Return the Discoms a visitor can still register, by name: active, with no login yet.

    A Discom has one portal login (FR-1.6), so one with a pending or active login is left out.
    It returns if that login is declined or deactivated.
    """
    taken = select(Login.organisation_id).where(*_current_member_login())
    query = (
        select(Organisation)
        .where(Organisation.status == "active", Organisation.id.not_in(taken))
        .order_by(func.lower(Organisation.name))
    )
    return list(db.scalars(query))


def _start_format_problems(db: Session, form: RegistrationStartForm) -> dict[str, str]:
    """Return the step 1 problems a visitor can fix, by field name."""
    problems = {}
    if _active_discom(db, form.organisation_id) is None:
        problems["organisation_id"] = "Choose your Discom from the list."
    if not re.fullmatch(EMAIL_PATTERN, form.email):
        problems["email"] = "Enter your official email address, such as name@yourdiscom.co.in."
    return problems


def _account_problems(db: Session, form: RegistrationForm, discom: Organisation) -> dict[str, str]:
    """Return the step 3 problems, by field name."""
    problems = {}
    if not re.fullmatch(USER_ID_PATTERN, form.user_id):
        problems["user_id"] = "Use 4 to 50 lowercase letters, numbers, dots, dashes or underscores."
    elif shape_problem(form.user_id):
        problems["user_id"] = shape_problem(form.user_id)
    elif _user_id_reserved(db, form.user_id, discom):
        problems["user_id"] = USER_ID_NOT_ALLOWED
    elif _user_id_taken(db, form.user_id):
        problems["user_id"] = "That User ID is taken. Choose another."
    password_problems = _password_problems(form.password, form.confirm_password, form.user_id)
    if password_problems:
        problems["password"] = " ".join(password_problems)
    return problems


def _active_discom(db: Session, organisation_id: str) -> Organisation | None:
    """Return the active Discom with this ID, or None for an unknown, inactive or malformed ID."""
    try:
        discom_id = uuid.UUID(organisation_id)
    except ValueError:
        return None
    discom = db.get(Organisation, discom_id)
    if discom is None or discom.status != "active":
        return None
    return discom


def _discom_has_member_login(db: Session, discom: Organisation) -> bool:
    """Return True when the Discom already has a pending or active Member login (FR-1.6)."""
    query = select(Login.id).where(Login.organisation_id == discom.id, *_current_member_login())
    return db.scalar(query) is not None


def _current_member_login() -> tuple[ColumnElement[bool], ...]:
    """Return the conditions for a Member login that holds its Discom's one place."""
    return (
        Login.login_type == "member",
        Login.status.in_(("pending", "active")),
        # NOT IN returns nothing if the list holds a NULL.
        Login.organisation_id.is_not(None),
    )


def _email_refusal(db: Session, discom: Organisation, email: str) -> str | None:
    """Return why this address may not register this Discom, for the audit only, or None."""
    # D-11: the email must be on the Discom's own domain, not a subdomain or a lookalike.
    # A public domain is refused here too, for a Discom listed before it was blocked.
    domain = email.rpartition("@")[2]
    if domain != discom.email_domain or domain in PUBLIC_EMAIL_DOMAINS:
        return "email_domain"
    if _current_email_taken(db, email):
        return "email_taken"
    return None


def _add_pending_member(db: Session, form: RegistrationForm, discom: Organisation, email: str) -> Login:
    """Add the Discom's Member login, pending until ITPED verifies it (P1-ACC-03)."""
    login = Login(
        user_id=form.user_id,
        email=email,
        login_type="member",
        organisation_id=discom.id,
        password_hash=hash_password(form.password),
        status="pending",
    )
    db.add(login)
    db.flush()
    return login


def _audit_code(db: Session, actor: Actor, result: str, details: dict[str, object]) -> None:
    """Audit asking for, or entering, a registration code. The code itself is never logged."""
    record(db, actor, "accounts.register_code", "login", None, result, details)


def _audit_registration(db: Session, actor: Actor, result: str, details: dict[str, object]) -> None:
    """Audit a registration request that created nothing; the request itself has no login yet."""
    record(db, actor, "accounts.register", "login", None, result, details)
