"""P1-ACC-03: Admin approves or declines a registration, and the Discom is emailed (FR-1.3, FR-1.4)."""

import smtplib
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.models import Login
from app.accounts.passwords import hash_password
from app.accounts.service import authenticate
from app.audit.models import AuditEvent
from app.core.email import send_email
from app.main import create_app
from tests.accounts.conftest import CLIENT, SignIn, build_login, csrf_client

APP = create_app()
PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password


def pending(engine: Engine, discom_status: str = "active") -> Login:
    """Save a pending Member registration and return it."""
    login = build_login("member", status="pending")
    login.password_hash = hash_password(PASSWORD)
    assert login.organisation is not None
    login.organisation.status = discom_status
    with Session(engine, expire_on_commit=False) as session:
        session.add(login)
        session.commit()
    return login


def decide(client: TestClient, login: Login, action: str, **data: str) -> int:
    url = f"/admin/registrations/{login.id}/{action}"
    return client.post(url, data=data, follow_redirects=False).status_code


def can_sign_in(engine: Engine, login: Login) -> bool:
    with Session(engine) as session:
        found = authenticate(session, login.user_id, PASSWORD, CLIENT[0], "test")
        session.rollback()
    return found is not None


def saved(engine: Engine, login: Login) -> Login:
    with Session(engine) as session:
        return session.get_one(Login, login.id)


def test_fr_1_3_pending_login_cannot_sign_in(
    sign_in: SignIn, engine: Engine, outbox: list[EmailMessage]
) -> None:
    admin = sign_in(APP, "admin")
    login = pending(engine)
    assert not can_sign_in(engine, login)
    client = csrf_client(APP)
    assert login.email in client.get("/admin/registrations").text

    assert decide(client, login, "approve") == 303

    assert can_sign_in(engine, login)
    assert (saved(engine, login).status, saved(engine, login).verified_by) == ("active", admin.id)
    assert login.email not in client.get("/admin/registrations").text


def test_fr_1_4_activation_sends_email(sign_in: SignIn, engine: Engine, outbox: list[EmailMessage]) -> None:
    sign_in(APP, "admin")
    login = pending(engine)
    client = csrf_client(APP)

    decide(client, login, "approve")
    # A second decision is refused, so the Discom is emailed once.
    assert decide(client, login, "approve") == 400
    assert decide(client, login, "decline", reason="Too late") == 400

    [message] = outbox
    assert message["To"] == login.email
    plain, formatted = (part.get_content() for part in message.iter_parts())
    for body in (plain, formatted):
        assert login.user_id in body
        assert "/login" in body
        assert PASSWORD not in body and "token" not in body
    with Session(engine) as session:
        actions = session.scalars(select(AuditEvent.action).where(AuditEvent.target_id == str(login.id)))
        assert "accounts.registration_approve" in actions.all()


def test_fr_1_3_decline_requires_reason(sign_in: SignIn, engine: Engine, outbox: list[EmailMessage]) -> None:
    sign_in(APP, "admin")
    login = pending(engine)
    client = csrf_client(APP)

    assert decide(client, login, "decline", reason="   ") == 400
    assert saved(engine, login).status == "pending"
    assert outbox == []

    assert decide(client, login, "decline", reason="Use your official address.") == 303

    assert (saved(engine, login).status, saved(engine, login).decline_reason) == (
        "declined",
        "Use your official address.",
    )
    assert "Use your official address." in outbox[0].get_body(("plain",)).get_content()  # type: ignore[union-attr]
    assert not can_sign_in(engine, login)


def test_p1_acc_03_approve_is_not_offered_for_a_deactivated_discom(sign_in: SignIn, engine: Engine) -> None:
    sign_in(APP, "admin")
    login = pending(engine, discom_status="inactive")
    client = csrf_client(APP)

    assert f"{login.id}/approve" not in client.get("/admin/registrations").text
    assert decide(client, login, "approve") == 400
    assert saved(engine, login).status == "pending"


@pytest.mark.parametrize("login_type", ["member", "reviewer", "approver"])
def test_p1_acc_03_only_admin_decides(login_type: str, sign_in: SignIn, engine: Engine) -> None:
    sign_in(APP, login_type)
    login = pending(engine)
    client = csrf_client(APP)

    assert client.get("/admin/registrations").status_code == 403
    assert decide(client, login, "approve") == 403
    assert saved(engine, login).status == "pending"


def test_p1_acc_03_a_failed_send_is_retried_and_blocks_nothing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    tries: list[str] = []

    def unreachable(*_: object, **__: object) -> None:
        tries.append("try")
        raise ConnectionRefusedError("no mail server")

    monkeypatch.setattr(smtplib, "SMTP", unreachable)

    context = {"discom": "Test", "reason": "Test"}
    send_email("a@example.test", "Subject", "email/registration_declined.txt", context)

    assert len(tries) == 6  # the first try and five retries
    assert "no mail server" in caplog.text


def test_p1_acc_03_the_queue_is_numbered_selectable_and_has_its_own_columns(
    sign_in: SignIn, engine: Engine
) -> None:
    sign_in(APP, "admin")
    login = pending(engine)

    page = csrf_client(APP).get("/admin/registrations").text

    assert "data-columns" in page and "data-export" in page
    for heading in ("Sr no", "Discom", "Email", "User ID", "Requested"):
        assert f">{heading}</th>" in page
    assert f">{login.user_id}</td>" in page
