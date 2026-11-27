"""Logins for account tests, and a stand-in for sign-in until sessions exist (P1-ACC-06)."""

import uuid
from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI, Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.guards import current_login
from app.accounts.models import Login


def build_login(login_type: str, status: str = "active", organisation_id: uuid.UUID | None = None) -> Login:
    """Return an unsaved login that meets every database rule, with a unique User ID."""
    is_member = login_type == "member"
    if is_member and organisation_id is None:
        organisation_id = uuid.uuid4()
    return Login(
        user_id=f"test.{uuid.uuid4().hex[:12]}",
        email="someone@example.test",
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
        login = build_login(login_type)
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
