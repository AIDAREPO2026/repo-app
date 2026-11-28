"""P1-ACC-05: a forgotten password is reset through a single-use emailed link (FR-1.2, FR-1.5)."""

import re
from datetime import timedelta
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.models import Login, LoginToken, UserSession
from app.accounts.passwords import hash_password, verify_password
from app.audit.models import AuditEvent
from app.core import captcha
from app.core.sessions import hash_token, new_token
from app.core.time import utc_now
from app.main import create_app
from tests.accounts.conftest import CLIENT, build_login, csrf_client, csrf_from

APP = create_app()
OLD = "Grid-Meter-2026"  # noqa: S105 - test values, not real passwords
NEW = "Feeder-Loss-2027"  # noqa: S105
LINK = re.compile(r"https://testserver/reset-password/(\S+)")
SENT = "If an account matches, we have sent a link."


@pytest.fixture(autouse=True)
def solved_captcha(monkeypatch: pytest.MonkeyPatch) -> None:
    # The CAPTCHA itself is tested in tests/core/test_captcha.py.
    monkeypatch.setattr(captcha, "verify", lambda payload, *_: payload == "solved")


def member(engine: Engine, status: str = "active", **values: object) -> Login:
    login = build_login("member", status=status)
    login.password_hash = hash_password(OLD)
    for name, value in values.items():
        setattr(login, name, value)
    with Session(engine, expire_on_commit=False) as session:
        session.add(login)
        session.commit()
    return login


def ask(identifier: str, solved: bool = True, **headers: str) -> tuple[int, str]:
    """Send the "Forgot password" form and return the status and the page that follows."""
    client = TestClient(APP, base_url="https://testserver", client=CLIENT)
    data = {"identifier": identifier, "altcha": "solved" if solved else ""}
    data["csrf_token"] = csrf_from(client.get("/forgot-password"))
    response = client.post("/forgot-password", data=data, headers=headers)
    return response.status_code, response.text


def choose(token: str, password: str = NEW) -> int:
    client = TestClient(APP, base_url="https://testserver", client=CLIENT)
    csrf = csrf_from(client.get("/login"))
    data = {"password": password, "confirm_password": password, "csrf_token": csrf}
    return client.post(f"/reset-password/{token}", data=data, follow_redirects=False).status_code


def link_token(outbox: list[EmailMessage]) -> str:
    match = LINK.search(outbox[-1].get_content())
    assert match, "the email has no reset link"
    return match.group(1)


def saved(engine: Engine, login: Login) -> Login:
    with Session(engine) as session:
        return session.get_one(Login, login.id)


def has_password(engine: Engine, login: Login, password: str) -> bool:
    password_hash = saved(engine, login).password_hash
    assert password_hash is not None
    return verify_password(password_hash, password)


def test_fr_1_5_reset_link_single_use(engine: Engine, outbox: list[EmailMessage]) -> None:
    login = member(engine)
    ask(login.user_id.upper())
    token = link_token(outbox)
    assert outbox[-1]["To"] == login.email

    assert choose(token, "short") == 400  # the policy applies, and the link still works
    assert choose(token) == 303
    assert has_password(engine, login, NEW)

    assert choose(token, "Another-Pass-2028") == 400
    assert has_password(engine, login, NEW)


def test_fr_1_5_reset_link_expires(engine: Engine, outbox: list[EmailMessage]) -> None:
    login = member(engine)
    ask(login.email.upper())
    token = link_token(outbox)
    with Session(engine) as session:
        session.execute(
            update(LoginToken)
            .where(LoginToken.token_hash == hash_token(token))
            .values(expires_at=utc_now() - timedelta(seconds=1))
        )
        session.commit()

    assert choose(token) == 400
    assert has_password(engine, login, OLD)


def test_fr_1_5_reset_ends_sessions(engine: Engine, outbox: list[EmailMessage]) -> None:
    login = member(engine, failed_count=3, locked_until=utc_now() + timedelta(minutes=15))
    with Session(engine) as session:
        session.add(
            UserSession(
                token_hash=hash_token(new_token()),
                login_id=login.id,
                csrf_token=new_token(),
                ip="127.0.0.1",
            )
        )
        session.commit()
    ask(login.user_id)

    assert choose(link_token(outbox)) == 303

    with Session(engine) as session:
        sessions = session.scalars(select(UserSession).where(UserSession.login_id == login.id)).all()
        actions = session.scalars(
            select(AuditEvent.action).where(AuditEvent.target_id == str(login.id))
        ).all()
    assert [item.end_reason for item in sessions] == ["password_reset"]
    assert (saved(engine, login).failed_count, saved(engine, login).locked_until) == (0, None)
    assert {"accounts.password_reset_request", "accounts.password_reset"} <= set(actions)


def test_fr_1_2_reset_requires_captcha(engine: Engine, outbox: list[EmailMessage]) -> None:
    login = member(engine)

    status, page = ask(login.user_id, solved=False)

    assert status == 400
    assert SENT not in page
    assert outbox == []


@pytest.mark.parametrize("status", ["pending", "declined", "deactivated"])
def test_fr_1_5_no_account_enumeration(status: str, engine: Engine, outbox: list[EmailMessage]) -> None:
    inactive = member(engine, status=status)
    active = member(engine)

    answers = [ask("no.such.user"), ask(inactive.user_id), ask(active.user_id), ask(active.user_id)]

    assert {code for code, _ in answers} == {200}
    assert all(SENT in page for _, page in answers)
    # Only the active account is emailed, and not again within the waiting time.
    assert [message["To"] for message in outbox] == [active.email]


def test_p1_acc_05_a_newer_link_replaces_the_older(engine: Engine, outbox: list[EmailMessage]) -> None:
    login = member(engine)
    ask(login.user_id)
    first = link_token(outbox)
    with Session(engine) as session:
        old = utc_now() - timedelta(minutes=6)
        session.execute(update(LoginToken).where(LoginToken.login_id == login.id).values(created_at=old))
        session.commit()
    ask(login.user_id)

    assert choose(first) == 400
    assert choose(link_token(outbox)) == 303


def test_p1_acc_05_the_link_ignores_the_host_header(engine: Engine, outbox: list[EmailMessage]) -> None:
    login = member(engine)

    ask(login.user_id, host="attacker.example")

    body = outbox[-1].get_content()
    assert "https://testserver/reset-password/" in body
    assert "attacker.example" not in body


def test_p1_acc_05_saving_a_password_is_announced_at_sign_in() -> None:
    page = csrf_client(APP).get("/login?done=password").text

    assert "Password saved. Sign in with it." in page
