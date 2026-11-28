"""Logins, clients and sign-in helpers shared by the account tests."""

import hashlib
import hmac
import re
import uuid
from collections.abc import Callable, Iterator
from email.message import EmailMessage

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.guards import current_login
from app.accounts.models import Login
from app.core import email
from app.core.sessions import CSRF_HEADER, VISITOR_CSRF_COOKIE
from tests.conftest import TEST_ENV

# A real address, because audit_event stores IPs as inet and TestClient's default is "testclient".
CLIENT = ("10.0.0.9", 50000)
CSRF_INPUT = re.compile(r'name="csrf_token" value="([^"]+)"')


def build_login(login_type: str, status: str = "active", organisation_id: uuid.UUID | None = None) -> Login:
    """Return an unsaved login that meets every database rule, with a unique User ID."""
    is_member = login_type == "member"
    if is_member and organisation_id is None:
        organisation_id = uuid.uuid4()
    user_id = f"test.{uuid.uuid4().hex[:12]}"
    # Unique, because no two current privileged accounts may share an email (FR-2.7).
    return Login(
        user_id=user_id,
        email=f"{user_id}@example.test",
        login_type=login_type,
        organisation_id=organisation_id,
        full_name=None if is_member else "Test Person",
        status=status,
    )


SignIn = Callable[[FastAPI, str], Login]


@pytest.fixture
def sign_in(engine: Engine) -> Iterator[SignIn]:
    """Save a login for real and make the app treat every request as signed in with it.

    The login is committed, because refusals are audited in their own transaction and the
    audit row refers to it.
    """
    apps: list[FastAPI] = []

    def signed_in_as(app: FastAPI, login_type: str) -> Login:
        # Saved deactivated, except Admins and Members: an active Reviewer or Approver left in
        # the database would break the one-per-role rules for later tests (FR-2.7).
        status = "active" if login_type in ("admin", "member") else "deactivated"
        login = build_login(login_type, status=status)
        with Session(engine, expire_on_commit=False) as session:
            session.add(login)
            session.commit()

        def fake_current_login(request: Request) -> Login:
            request.state.session_id = uuid.uuid4()
            return login

        app.dependency_overrides[current_login] = fake_current_login
        apps.append(app)
        return login

    yield signed_in_as
    for app in apps:
        app.dependency_overrides.clear()


def csrf_client(app: FastAPI) -> TestClient:
    """A client that sends a valid visitor CSRF token, so POST routes reach their guard."""
    client = TestClient(app, client=CLIENT)
    client.cookies.set(VISITOR_CSRF_COOKIE, "cookie-value")
    token = hmac.new(TEST_ENV["SECRET_KEY"].encode(), b"cookie-value", hashlib.sha256).hexdigest()
    client.headers[CSRF_HEADER] = token
    return client


def csrf_from(response: Response) -> str:
    """Return the CSRF token in a page's form."""
    match = CSRF_INPUT.search(response.text)
    assert match, "the page has no CSRF field"
    return match.group(1)


def submit_sign_in(client: TestClient, user_id: str, password: str, next_path: str = "") -> Response:
    """Sign in through the real form, CSRF token included."""
    token = csrf_from(client.get("/login"))
    form = {"user_id": user_id, "password": password, "next": next_path, "csrf_token": token}
    return client.post("/login", data=form, follow_redirects=False)


class FakeSMTP:
    """Stands in for smtplib.SMTP and keeps every message sent."""

    sent: list[EmailMessage] = []

    def __init__(self, host: str, port: int, timeout: float) -> None:
        pass

    def __enter__(self) -> "FakeSMTP":
        return self

    def __exit__(self, *_: object) -> None:
        pass

    def send_message(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.fixture
def outbox(monkeypatch: pytest.MonkeyPatch) -> list[EmailMessage]:
    FakeSMTP.sent = []
    monkeypatch.setattr(email.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP.sent


@pytest.fixture
def no_active_reviewers_or_approvers(engine: Engine) -> Iterator[None]:
    """Start and end each test with no active Reviewer or Approver, because only one of each may exist."""

    def clear() -> None:
        with Session(engine) as session:
            session.execute(
                update(Login)
                .where(Login.login_type.in_(("reviewer", "approver")), Login.status == "active")
                .values(status="deactivated")
            )
            session.commit()

    clear()
    yield
    clear()
