"""Route guards: every route declares which login types may use it (FR-2.1, security.md access control).

Use `require_login_type("admin")` on a protected route, or `public_route` on a route open to
visitors. The route registry test fails for any route that has neither.
"""

from typing import Annotated
from urllib.parse import quote

from fastapi import Depends, HTTPException, Request

from app.accounts.models import Login
from app.audit.service import Actor, record
from app.core.constants import LOGIN_TYPES
from app.core.sessions import client_ip, user_agent

LOGIN_PATH = "/login"


def current_login(request: Request) -> Login | None:
    """Return the signed-in login, or None for a visitor.

    `app.core.sessions.load_session` puts the login and session ID on request.state
    before every route runs.
    """
    return getattr(request.state, "login", None)


def actor_for(request: Request, login: Login) -> Actor:
    """Describe a signed-in login, with its session and device, for the audit trail."""
    return Actor(
        kind=login.login_type,
        login_id=login.id,
        session_id=getattr(request.state, "session_id", None),
        ip=client_ip(request),
        user_agent=user_agent(request),
    )


class LoginTypeGuard:
    """A FastAPI dependency that returns the current login if its type is allowed, or refuses."""

    def __init__(self, login_types: tuple[str, ...]) -> None:
        """Remember the allowed login types, refusing names that are not login types."""
        unknown = set(login_types) - set(LOGIN_TYPES)
        if not login_types or unknown:
            raise ValueError(f"Allowed login types must be some of {LOGIN_TYPES}, not {login_types}")
        self.login_types = login_types

    def __call__(self, request: Request, login: Annotated[Login | None, Depends(current_login)]) -> Login:
        """Send visitors to sign in, refuse a wrong login type with 403, and return the login."""
        if login is None:
            # Only the path, never a full URL, so the sign-in page cannot be used as an open redirect.
            location = f"{LOGIN_PATH}?next={quote(request.url.path)}"
            raise HTTPException(status_code=303, headers={"Location": location})
        if login.login_type not in self.login_types:
            audit_refusal(request, login)
            raise HTTPException(status_code=403)
        return login


def require_login_type(*login_types: str) -> LoginTypeGuard:
    """Return the guard for a route open only to these login types."""
    return LoginTypeGuard(login_types)


def public_route() -> None:
    """Mark a route as open to everyone, including visitors: `dependencies=[Depends(public_route)]`."""


def audit_refusal(request: Request, login: Login) -> None:
    """Record a refused request with result denied.

    Uses its own transaction, because the route's session rolls back when the guard raises.
    """
    with request.app.state.session_factory() as db:
        details = {"method": request.method, "reason": "wrong_login_type"}
        record(
            db,
            actor_for(request, login),
            "accounts.access",
            "route",
            request.url.path[:64],
            "denied",
            details,
        )
        db.commit()
