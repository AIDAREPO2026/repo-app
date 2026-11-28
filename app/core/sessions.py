"""Server-side sessions, the idle timeout and CSRF protection (FR-1.7, SRS 2.3, security.md sessions).

Two app-wide dependencies run before every route, in this order:

1. `load_session` reads the `drr_session` cookie, ends the session if it has been idle
   for more than 30 minutes, and puts the login, session ID and CSRF token on
   `request.state`, where `app.accounts.guards.current_login` reads them. A session still
   waiting for its second factor puts the login on `request.state.mfa_login` instead, so
   every guarded route treats it as signed out (FR-2.8).
2. `check_csrf` refuses any POST, PUT, PATCH or DELETE whose token does not match.

They are dependencies rather than middleware, so they stay synchronous, show up in the
route registry, and use the same database session factory as everything else.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import Login, UserSession
from app.audit.service import Actor, record
from app.core.constants import IDLE_TIMEOUT_MINUTES
from app.core.time import utc_now

SESSION_COOKIE = "drr_session"
# Visitors have no session, so their forms are tied to this cookie instead.
VISITOR_CSRF_COOKIE = "drr_csrf"
CSRF_FIELD = "csrf_token"
CSRF_HEADER = "x-csrf-token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Writing last_seen_at on every request would turn every page view into a database write.
LAST_SEEN_INTERVAL = timedelta(minutes=1)


def hash_token(token: str) -> bytes:
    """Return the SHA-256 of a session token. Only this hash is stored."""
    return hashlib.sha256(token.encode()).digest()


def new_token() -> str:
    """Return 32 random bytes, URL-safe, for a session token or CSRF token."""
    return secrets.token_urlsafe(32)


def load_session(request: Request) -> None:
    """Put the signed-in login, its session ID and the CSRF token for this request on request.state."""
    request.state.login = None
    request.state.mfa_login = None
    request.state.session_id = None
    request.state.csrf_token = visitor_csrf_token(request)
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return
    with request.app.state.session_factory() as db:
        found = _active_session(db, token)
        if found is None:
            return
        user_session, login = found
        if _is_idle(user_session):
            end_session(db, user_session, login, "idle", client_ip(request))
            db.commit()
            return
        _touch(user_session)
        db.commit()
    if user_session.mfa_pending:
        request.state.mfa_login = login
    else:
        request.state.login = login
    request.state.session_id = user_session.id
    request.state.csrf_token = user_session.csrf_token


async def check_csrf(request: Request, _: Annotated[None, Depends(load_session)]) -> None:
    """Refuse a state-changing request whose CSRF token is missing or wrong, with 403.

    Async only because reading a submitted form is async in Starlette. The form is
    cached, so the route still reads it as usual.
    """
    if request.method in SAFE_METHODS:
        return
    sent: object = request.headers.get(CSRF_HEADER)
    if sent is None:
        form = await request.form()
        sent = form.get(CSRF_FIELD)
    expected = request.state.csrf_token
    if not isinstance(sent, str) or not expected or not hmac.compare_digest(sent, expected):
        raise HTTPException(status_code=403)


def start_session(
    db: Session, login: Login, request: Request, response: Response, mfa_pending: bool = False
) -> UserSession:
    """Create a new session for a login that has just signed in, and set its cookie.

    Any session this browser already had is ended first, so the session token always
    changes at sign-in and again after the second factor. With mfa_pending the session
    can reach only the code page until the second factor is given (FR-2.8).
    """
    old_token = request.cookies.get(SESSION_COOKIE)
    if old_token:
        found = _active_session(db, old_token)
        if found is not None:
            end_session(db, found[0], found[1], "replaced", client_ip(request))
    token = new_token()
    user_session = UserSession(
        id=uuid.uuid4(),
        token_hash=hash_token(token),
        login_id=login.id,
        csrf_token=new_token(),
        mfa_pending=mfa_pending,
        ip=client_ip(request),
        user_agent=user_agent(request),
    )
    db.add(user_session)
    db.flush()
    record(
        db,
        _actor(login, user_session, client_ip(request)),
        "accounts.login",
        "login",
        str(login.id),
        "success",
        {"mfa_pending": mfa_pending},
    )
    set_cookie(response, SESSION_COOKIE, token)
    return user_session


def signed_in_sessions(db: Session, login: Login) -> list[UserSession]:
    """Return the login's signed-in sessions, oldest first, ending any left idle on the way.

    A closed browser never comes back to be ended, so counting without this would let
    abandoned sessions hold a Discom's places for good (FR-2.3).
    """
    query = (
        select(UserSession)
        .where(UserSession.login_id == login.id, UserSession.ended_at.is_(None))
        .where(UserSession.mfa_pending.is_(False))
        .order_by(UserSession.created_at)
    )
    signed_in = []
    for user_session in db.scalars(query):
        if _is_idle(user_session):
            end_session(db, user_session, login, "idle", str(user_session.ip))
        else:
            signed_in.append(user_session)
    return signed_in


def end_session(
    db: Session,
    user_session: UserSession,
    login: Login,
    reason: str,
    ip: str | None,
    by: Actor | None = None,
) -> None:
    """End a session now, so its token stops working on the next request, and audit it.

    by names who ended it when that is not the session itself, such as another device.
    """
    user_session.ended_at = utc_now()
    user_session.end_reason = reason
    db.flush()
    action = "accounts.logout" if reason == "logout" else "accounts.session_end"
    record(
        db,
        by or _actor(login, user_session, ip),
        action,
        "session",
        str(user_session.id),
        "success",
        {"reason": reason},
    )


def set_cookie(response: Response, name: str, value: str) -> None:
    """Set a cookie with the flags security.md requires, and no Domain, so it stays on this host."""
    response.set_cookie(name, value, httponly=True, secure=True, samesite="lax", path="/")


def clear_session_cookie(response: Response) -> None:
    """Remove the session cookie from the browser."""
    response.delete_cookie(SESSION_COOKIE, httponly=True, secure=True, samesite="lax", path="/")


def new_visitor_csrf_cookie(request: Request) -> str | None:
    """Make a CSRF cookie value for a visitor who has none, and the matching token for this page.

    Returns the cookie value to set on the response, or None when no new cookie is needed.
    Call it before rendering the form, so the page carries the token.
    """
    if request.state.login is not None or request.cookies.get(VISITOR_CSRF_COOKIE):
        return None
    value = new_token()
    request.state.csrf_token = _sign(request, value)
    return value


def visitor_csrf_token(request: Request) -> str | None:
    """Return the CSRF token for a visitor's forms: an HMAC of their CSRF cookie.

    Signing it means a cookie planted by another site or subdomain is useless without
    the matching token, which only this app can make.
    """
    value = request.cookies.get(VISITOR_CSRF_COOKIE)
    if not value:
        return None
    return _sign(request, value)


def client_ip(request: Request) -> str:
    """Return the client's IP address as Nginx passed it on."""
    return request.client.host if request.client else "0.0.0.0"  # noqa: S104 - a placeholder, not a bind


def user_agent(request: Request) -> str:
    """Return the browser's User-Agent, cut to the stored length."""
    return request.headers.get("user-agent", "")[:500]


def _sign(request: Request, value: str) -> str:
    """Return the HMAC-SHA256 of a value, keyed with the app's secret key."""
    key = request.app.state.secret_key.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def _active_session(db: Session, token: str) -> tuple[UserSession, Login] | None:
    """Return the session for a cookie token and its login, if the session has not ended."""
    query = (
        select(UserSession, Login)
        .join(Login, Login.id == UserSession.login_id)
        .where(UserSession.token_hash == hash_token(token), UserSession.ended_at.is_(None))
    )
    row = db.execute(query).one_or_none()
    if row is None:
        return None
    return row[0], row[1]


def _is_idle(user_session: UserSession) -> bool:
    """Return True when the session has had no request for more than 30 minutes (FR-1.7)."""
    return utc_now() - user_session.last_seen_at > timedelta(minutes=IDLE_TIMEOUT_MINUTES)


def _touch(user_session: UserSession) -> None:
    """Move last_seen_at to now, at most once a minute."""
    now = utc_now()
    if now - user_session.last_seen_at >= LAST_SEEN_INTERVAL:
        user_session.last_seen_at = now


def _actor(login: Login, user_session: UserSession, ip: str | None) -> Actor:
    """Describe a login acting through a session, for the audit trail."""
    return Actor(kind=login.login_type, login_id=login.id, session_id=user_session.id, ip=ip)
