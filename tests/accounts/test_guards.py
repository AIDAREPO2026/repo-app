"""Every route declares who may use it, and the guards refuse everyone else (FR-2.1)."""

import hashlib
import hmac
import re

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.guards import LoginTypeGuard, public_route, require_login_type
from app.audit.models import AuditEvent
from app.core.constants import LOGIN_TYPES
from app.core.sessions import CSRF_HEADER, VISITOR_CSRF_COOKIE
from app.main import create_app
from tests.accounts.conftest import SignIn
from tests.conftest import TEST_ENV

APP = create_app()
# A real address, because audit_event stores IPs as inet and TestClient's default is "testclient".
CLIENT = ("10.0.0.9", 50000)


def dependency_calls(dependant: Dependant) -> list[object]:
    """Return every dependency a route uses, including dependencies of dependencies."""
    calls: list[object] = []
    for dependency in dependant.dependencies:
        calls.append(dependency.call)
        calls.extend(dependency_calls(dependency))
    return calls


def api_routes(app: FastAPI) -> list[RouteContext]:
    """Return every API route as served, with the dependencies of the routers it was included through."""
    return [
        context for context in iter_route_contexts(app.routes) if isinstance(context.original_route, APIRoute)
    ]


def other_routes(app: FastAPI) -> list[str]:
    """Return served paths that are not API routes, such as mounts."""
    return [
        str(context.path)
        for context in iter_route_contexts(app.routes)
        if not isinstance(context.original_route, APIRoute)
    ]


def guard_of(route: RouteContext) -> LoginTypeGuard | None:
    """Return the login type guard on a route, if it has one."""
    for call in dependency_calls(route.dependant):
        if isinstance(call, LoginTypeGuard):
            return call
    return None


def unguarded_routes(app: FastAPI) -> list[str]:
    """Return the routes that declare neither allowed login types nor public_route."""
    missing = []
    for route in api_routes(app):
        if guard_of(route) is None and public_route not in dependency_calls(route.dependant):
            missing.append(f"{sorted(route.methods or [])} {route.path}")
    return missing


def sample_path(path: str) -> str:
    """Fill path parameters with a valid-looking ID, so the guard runs before any lookup."""
    return re.sub(r"\{[^}]+\}", "00000000-0000-4000-8000-000000000000", path)


def method_of(route: RouteContext) -> str:
    """Return the one HTTP method a route answers (GET for pages, POST for actions)."""
    return sorted(route.methods or ["GET"])[0]


GUARDED = [(route, guard) for route in api_routes(APP) if (guard := guard_of(route)) is not None]
WRONG_TYPES = [
    (method_of(route), sample_path(str(route.path)), login_type)
    for route, guard in GUARDED
    for login_type in LOGIN_TYPES
    if login_type not in guard.login_types
]
EVERY_GUARDED = [(method_of(route), sample_path(str(route.path))) for route, _ in GUARDED]
# Pages only: actions such as sign-out need a real session, and are tested with sessions.
GUARDED_PAGES = [
    (sample_path(str(route.path)), guard.login_types[0])
    for route, guard in GUARDED
    if method_of(route) == "GET"
]


def client_with_csrf() -> TestClient:
    """A client that sends a valid visitor CSRF token, so POST routes reach their guard."""
    client = TestClient(APP, client=CLIENT)
    client.cookies.set(VISITOR_CSRF_COOKIE, "cookie-value")
    token = hmac.new(TEST_ENV["SECRET_KEY"].encode(), b"cookie-value", hashlib.sha256).hexdigest()
    client.headers[CSRF_HEADER] = token
    return client


def test_p1_acc_08_every_route_is_guarded() -> None:
    assert len(GUARDED) >= 4
    assert unguarded_routes(APP) == []
    # Static files are the only served paths outside the API routes.
    assert other_routes(APP) == ["/static"]


def test_p1_acc_08_registry_test_catches_an_unguarded_route() -> None:
    app = create_app()
    extra = APIRouter()

    @extra.get("/forgot-to-guard")
    def forgot_to_guard() -> None:
        """A route someone added without a guard."""

    @extra.get("/guarded", dependencies=[Depends(require_login_type("admin"))])
    def guarded() -> None:
        """A route with a guard."""

    app.include_router(extra)

    assert unguarded_routes(app) == ["['GET'] /forgot-to-guard"]


def test_p1_acc_08_guard_refuses_unknown_login_type() -> None:
    with pytest.raises(ValueError, match="login types"):
        require_login_type("visitor")


@pytest.mark.parametrize(("method", "path"), EVERY_GUARDED)
def test_p1_acc_08_visitor_is_sent_to_sign_in(method: str, path: str) -> None:
    response = client_with_csrf().request(method, path, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == f"/login?next={path}"


@pytest.mark.parametrize(("method", "path", "login_type"), WRONG_TYPES)
def test_p1_acc_08_wrong_login_type_refused_and_audited(
    method: str, path: str, login_type: str, sign_in: SignIn, engine: Engine
) -> None:
    login = sign_in(APP, login_type)

    response = client_with_csrf().request(method, path)

    assert response.status_code == 403
    with Session(engine) as session:
        refusal = session.scalars(select(AuditEvent).where(AuditEvent.actor_login_id == login.id)).one()
    assert (refusal.action, refusal.result, refusal.target_id) == ("accounts.access", "denied", path)
    assert refusal.session_id is not None


@pytest.mark.parametrize(("path", "login_type"), GUARDED_PAGES)
def test_p1_acc_08_allowed_login_type_gets_in(path: str, login_type: str, sign_in: SignIn) -> None:
    sign_in(APP, login_type)

    assert TestClient(APP, client=CLIENT).get(path).status_code == 200
