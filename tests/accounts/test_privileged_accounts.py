"""P1-ACC-09: named Admin, Reviewer and Approver accounts, set-password links and the CLI (FR-2.7)."""

import re
import uuid
from datetime import timedelta
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts import cli
from app.accounts.models import Login, LoginToken, UserSession
from app.accounts.passwords import hash_password
from app.accounts.schemas import PersonForm, PrivilegedAccountForm
from app.accounts.service import (
    AccountRuleError,
    authenticate,
    create_privileged_account,
    deactivate_account,
    reassign_account,
    set_reviewer_role,
)
from app.audit.models import AuditEvent
from app.audit.service import SYSTEM
from app.main import create_app
from tests.accounts.conftest import (
    CLIENT,
    SignIn,
    build_login,
    csrf_client,
    csrf_from,
    submit_sign_in,
)

APP = create_app()
PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password
BASE_URL = "https://testserver/"
LINK = re.compile(r"https://testserver/set-password/(\S+)")


# Only one active Reviewer of each kind and one active Approver may exist (FR-2.7).
pytestmark = pytest.mark.usefixtures("no_active_reviewers_or_approvers")


def person(name: str = "Asha Rao") -> dict[str, str]:
    """Return form values for a new person with a unique User ID and email."""
    tag = uuid.uuid4().hex[:10]
    user_id = "zq." + "".join("bfghjkqvxz"[int(c, 16) % 10] for c in tag)
    return {"full_name": name, "email": f"{tag}@itped.example", "user_id": user_id}


def account_form(login_type: str, is_alternate: bool = False) -> PrivilegedAccountForm:
    return PrivilegedAccountForm(login_type=login_type, is_alternate=is_alternate, **person())


def link_token(message: EmailMessage) -> str:
    match = LINK.search(message.get_content())
    assert match, "the email has no set-password link"
    return match.group(1)


def committed_account(engine: Engine, login_type: str, outbox: list[EmailMessage]) -> tuple[Login, str]:
    """Create an account through the service, commit it, and return it with its link token."""
    with Session(engine, expire_on_commit=False) as session:
        login = create_privileged_account(session, SYSTEM, account_form(login_type), BASE_URL)
        session.commit()
    return login, link_token(outbox[-1])


def test_fr_2_7_admin_creates_privileged_accounts(
    sign_in: SignIn, engine: Engine, outbox: list[EmailMessage]
) -> None:
    admin = sign_in(APP, "admin")
    values = person("Meera Iyer") | {"login_type": "approver"}

    response = csrf_client(APP).post("/admin/accounts", data=values, follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/accounts?done=created"
    with Session(engine) as session:
        created = session.scalars(select(Login).where(Login.user_id == values["user_id"])).one()
        actions = session.scalars(
            select(AuditEvent.action).where(AuditEvent.target_id == str(created.id)).order_by(AuditEvent.id)
        ).all()
        actor_ids = session.scalars(
            select(AuditEvent.actor_login_id).where(AuditEvent.target_id == str(created.id))
        )
        assert set(actor_ids) == {admin.id}
    assert (created.login_type, created.status, created.full_name) == ("approver", "active", "Meera Iyer")
    assert created.password_hash is None
    assert actions == ["accounts.create", "accounts.set_password_link"]
    assert [message["To"] for message in outbox] == [values["email"]]
    assert values["user_id"] in outbox[0].get_content()
    page = csrf_client(APP).get("/admin/accounts")
    assert "Meera Iyer" in page.text
    assert "Waiting for password" in page.text


@pytest.mark.parametrize("login_type", ["member", "reviewer", "approver"])
def test_fr_2_7_only_admin_reaches_account_screens(login_type: str, sign_in: SignIn) -> None:
    sign_in(APP, login_type)

    assert csrf_client(APP).get("/admin/accounts").status_code == 403


def test_fr_2_7_single_active_approver(db: Session, outbox: list[EmailMessage]) -> None:
    create_privileged_account(db, SYSTEM, account_form("approver"), BASE_URL)

    with pytest.raises(AccountRuleError, match="already an active Approver"):
        create_privileged_account(db, SYSTEM, account_form("approver"), BASE_URL)

    # The database holds the same rule, for two Admins acting at once.
    second = build_login("approver")
    db.add(second)
    with pytest.raises(IntegrityError, match="uq_login_one_active_approver"):
        db.flush()


def test_fr_2_7_one_primary_and_one_alternate_reviewer(db: Session, outbox: list[EmailMessage]) -> None:
    primary = create_privileged_account(db, SYSTEM, account_form("reviewer"), BASE_URL)
    alternate = create_privileged_account(db, SYSTEM, account_form("reviewer", is_alternate=True), BASE_URL)

    with pytest.raises(AccountRuleError, match="already an active alternate Reviewer"):
        create_privileged_account(db, SYSTEM, account_form("reviewer", is_alternate=True), BASE_URL)

    set_reviewer_role(db, SYSTEM, primary, is_alternate=True)
    # The rule is checked at commit; this checks it now, inside the test's transaction.
    db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    assert (primary.is_alternate, alternate.is_alternate) == (True, False)


def test_fr_2_7_no_shared_privileged_accounts(db: Session, outbox: list[EmailMessage]) -> None:
    first = create_privileged_account(db, SYSTEM, account_form("admin"), BASE_URL)
    same_email = account_form("admin").model_copy(update={"email": first.email.upper()})

    with pytest.raises(AccountRuleError, match="Each person needs their own"):
        create_privileged_account(db, SYSTEM, same_email, BASE_URL)


def test_fr_2_7_deactivation_ends_sessions(engine: Engine) -> None:
    target = build_login("admin")
    target.password_hash = hash_password(PASSWORD)
    with Session(engine, expire_on_commit=False) as session:
        session.add(target)
        session.commit()
    client = TestClient(APP, base_url="https://testserver", client=CLIENT)
    assert submit_sign_in(client, target.user_id, PASSWORD).status_code == 303
    assert client.get("/dashboard/admin").status_code == 200

    with Session(engine) as session:
        deactivate_account(session, SYSTEM, build_login("admin"), session.get_one(Login, target.id))
        session.commit()

    response = client.get("/dashboard/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/login")
    with Session(engine) as session:
        ended = session.scalars(select(UserSession.end_reason).where(UserSession.login_id == target.id)).all()
        assert ended == ["admin"]
        assert authenticate(session, target.user_id, PASSWORD, "10.0.0.9", "test") is None


def test_fr_2_7_admin_cannot_deactivate_own_account(db: Session) -> None:
    admin = build_login("admin")
    db.add(admin)
    db.flush()

    with pytest.raises(AccountRuleError, match="your own account"):
        deactivate_account(db, SYSTEM, admin, admin)


def test_p1_acc_09_reassign_replaces_the_person(db: Session, outbox: list[EmailMessage]) -> None:
    old = create_privileged_account(db, SYSTEM, account_form("reviewer", is_alternate=True), BASE_URL)

    new = reassign_account(
        db, SYSTEM, build_login("admin"), old, PersonForm(**person("Ravi Menon")), BASE_URL
    )

    assert old.status == "deactivated"
    assert (new.login_type, new.is_alternate, new.status, new.full_name) == (
        "reviewer",
        True,
        "active",
        "Ravi Menon",
    )
    assert outbox[-1]["To"] == new.email


def test_p1_acc_09_refused_reassign_changes_nothing(
    sign_in: SignIn, engine: Engine, outbox: list[EmailMessage]
) -> None:
    sign_in(APP, "admin")
    old, _ = committed_account(engine, "approver", outbox)
    taken = person() | {"user_id": old.user_id}

    response = csrf_client(APP).post(f"/admin/accounts/{old.id}/reassign", data=taken)

    assert response.status_code == 400
    assert "already in use" in response.text
    with Session(engine) as session:
        assert session.get_one(Login, old.id).status == "active"


def test_p1_acc_09_set_password_link_single_use(engine: Engine, outbox: list[EmailMessage]) -> None:
    login, token = committed_account(engine, "approver", outbox)
    client = TestClient(APP, base_url="https://testserver", client=CLIENT)
    path = f"/set-password/{token}"
    page = client.get(path)
    assert page.status_code == 200

    mismatch = {"password": PASSWORD, "confirm_password": "other", "csrf_token": csrf_from(page)}
    assert "do not match" in client.post(path, data=mismatch).text

    form = mismatch | {"confirm_password": PASSWORD}
    response = client.post(path, data=form, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    reused = client.post(path, data=form)
    assert reused.status_code == 400
    assert "already been used or has expired" in reused.text
    assert client.get(path).status_code == 400
    with Session(engine) as session:
        assert authenticate(session, login.user_id, PASSWORD, "10.0.0.9", "test") is not None
        session.rollback()


def test_p1_acc_09_set_password_link_expires(engine: Engine, outbox: list[EmailMessage]) -> None:
    login, token = committed_account(engine, "admin", outbox)
    with Session(engine) as session:
        session.execute(
            update(LoginToken)
            .where(LoginToken.login_id == login.id)
            .values(expires_at=LoginToken.created_at - timedelta(seconds=1))
        )
        session.commit()

    client = TestClient(APP, base_url="https://testserver", client=CLIENT)
    assert client.get(f"/set-password/{token}").status_code == 400


def test_p1_acc_09_create_admin_command(engine: Engine, monkeypatch: pytest.MonkeyPatch) -> None:
    values = person("First Admin")
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: PASSWORD)
    argv = [
        "create-admin",
        "--user-id",
        values["user_id"],
        "--full-name",
        "First Admin",
        "--email",
        values["email"],
    ]

    assert cli.main(argv) == 0

    with Session(engine) as session:
        assert authenticate(session, values["user_id"], PASSWORD, "10.0.0.9", "test") is not None
        session.rollback()
        created = session.scalars(select(Login).where(Login.user_id == values["user_id"])).one()
        audit = session.scalars(select(AuditEvent).where(AuditEvent.target_id == str(created.id))).one()
    assert (audit.action, audit.actor_kind) == ("accounts.create", "system")


def test_p1_acc_09_create_admin_command_refuses_weak_password(monkeypatch: pytest.MonkeyPatch) -> None:
    values = person()
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "short")
    argv = ["create-admin", "--user-id", values["user_id"], "--full-name", "A", "--email", values["email"]]

    assert cli.main(argv) == 1
