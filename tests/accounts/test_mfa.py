"""P1-ACC-10: the second sign-in step, by authenticator app or emailed code (FR-2.8)."""

import re
from datetime import timedelta
from email.message import EmailMessage
from typing import Any

import pyotp
import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts import cli
from app.accounts.mfa import decrypt_secret, encrypt_secret
from app.accounts.models import Login, LoginAttempt, LoginToken, UserSession
from app.accounts.passwords import hash_password
from app.accounts.service import AccountRuleError, reset_mfa, turn_off_member_mfa
from app.accounts.tokens import issue_email_code, use_email_code
from app.audit.models import AuditEvent
from app.audit.service import SYSTEM
from app.core.constants import EMAIL_CODE_MAX_TRIES, LOCKOUT_ATTEMPTS
from app.core.sessions import CSRF_HEADER, SESSION_COOKIE
from app.core.time import utc_now
from app.main import create_app
from tests.accounts.conftest import CLIENT, SignIn, build_login, csrf_client, csrf_from, submit_sign_in
from tests.accounts.test_guards import EVERY_GUARDED

# Only one active Reviewer of each kind and one active Approver may exist (FR-2.7).
pytestmark = pytest.mark.usefixtures("no_active_reviewers_or_approvers")

APP = create_app()
PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password
CODE_IN_EMAIL = re.compile(r"code is (\d{6})")


@pytest.fixture(scope="module")
def password_hash() -> str:
    return hash_password(PASSWORD)


def saved_login(engine: Engine, password_hash: str, login_type: str, **fields: Any) -> Login:
    """Save an active login with the test password and any MFA fields given."""
    login = build_login(login_type)
    login.password_hash = password_hash
    for name, value in fields.items():
        setattr(login, name, value)
    with Session(engine, expire_on_commit=False) as session:
        session.add(login)
        session.commit()
    return login


def app_login(engine: Engine, password_hash: str, login_type: str = "admin") -> tuple[Login, str]:
    """Save a login enrolled with an authenticator app, and return it with the plain secret."""
    secret = pyotp.random_base32()
    login = saved_login(
        engine, password_hash, login_type, mfa_method="totp", mfa_totp_secret=encrypt_secret(secret)
    )
    return login, secret


def new_client() -> TestClient:
    # HTTPS, because the session cookie is Secure and is not sent over plain HTTP.
    return TestClient(APP, base_url="https://testserver", client=CLIENT)


def password_step(login: Login, next_path: str = "") -> TestClient:
    """Sign in with the password and return the client, now waiting for its second factor."""
    client = new_client()
    response = submit_sign_in(client, login.user_id, PASSWORD, next_path)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/mfa")
    return client


def post_form(client: TestClient, path: str, data: dict[str, str], page: str = "/mfa") -> Response:
    """Post a form with the CSRF token from the page it sits on."""
    token = csrf_from(client.get(page))
    return client.post(path, data={**data, "csrf_token": token}, follow_redirects=False)


def submit_code(client: TestClient, code: str, method: str = "totp") -> Response:
    return post_form(client, "/mfa", {"code": code, "method": method})


def stored_login(engine: Engine, login: Login) -> Login:
    with Session(engine) as session:
        return session.get_one(Login, login.id)


def audit_actions(engine: Engine, login: Login) -> list[str]:
    with Session(engine) as session:
        query = select(AuditEvent.action).where(AuditEvent.target_id == str(login.id)).order_by(AuditEvent.id)
        return list(session.scalars(query))


def emailed_code(outbox: list[EmailMessage]) -> str:
    match = CODE_IN_EMAIL.search(outbox[-1].get_content())
    assert match, "the email has no code"
    return match.group(1)


@pytest.mark.parametrize("login_type", ["admin", "reviewer", "approver"])
def test_fr_2_8_privileged_mfa_required(engine: Engine, password_hash: str, login_type: str) -> None:
    login = saved_login(engine, password_hash, login_type)

    client = password_step(login)

    dashboard = client.get(f"/dashboard/{login_type}", follow_redirects=False)
    assert (dashboard.status_code, dashboard.headers["location"]) == (303, "/mfa")
    # Not enrolled yet, so the code page asks for a method first.
    assert "Use an authenticator app" in client.get("/mfa").text


def test_fr_2_8_pending_mfa_blocks_all_routes(engine: Engine, password_hash: str) -> None:
    login, _ = app_login(engine, password_hash)
    client = password_step(login)
    # The session's own CSRF token, so POST routes reach their guard.
    client.headers[CSRF_HEADER] = csrf_from(client.get("/mfa"))

    for method, path in EVERY_GUARDED:
        response = client.request(method, path, follow_redirects=False)
        assert (response.status_code, response.headers.get("location")) == (303, "/mfa"), (method, path)


def test_fr_2_8_enrol_with_authenticator_app(engine: Engine, password_hash: str) -> None:
    login = saved_login(engine, password_hash, "admin")
    client = password_step(login, "/admin/accounts")
    pending_cookie = client.cookies[SESSION_COOKIE]

    post_form(client, "/mfa/setup", {"method": "totp", "next": "/admin/accounts"})
    page = client.get("/mfa", params={"method": "totp"})
    assert 'src="data:image/svg+xml;base64,' in page.text
    secret = decrypt_secret(stored_login(engine, login).mfa_totp_secret or "")
    assert secret in page.text
    response = post_form(
        client, "/mfa", {"code": pyotp.TOTP(secret).now(), "method": "totp", "next": "/admin/accounts"}
    )

    assert (response.status_code, response.headers["location"]) == (303, "/admin/accounts")
    assert client.get("/admin/accounts").status_code == 200
    # FR-2.8, security.md: the session token changes after the second factor.
    assert client.cookies[SESSION_COOKIE] != pending_cookie
    enrolled = stored_login(engine, login)
    assert (enrolled.mfa_method, enrolled.mfa_enrolled_at is not None) == ("totp", True)
    assert "accounts.mfa_enrol" in audit_actions(engine, login)


def test_fr_2_8_enrol_with_email_code(engine: Engine, password_hash: str, outbox: list[EmailMessage]) -> None:
    login = saved_login(engine, password_hash, "admin")
    client = password_step(login)

    post_form(client, "/mfa/setup", {"method": "email"})
    response = submit_code(client, emailed_code(outbox), method="email")

    assert (response.status_code, response.headers["location"]) == (303, "/dashboard/admin")
    assert stored_login(engine, login).mfa_method == "email"


def test_fr_2_8_email_code_sent_at_sign_in(
    engine: Engine, password_hash: str, outbox: list[EmailMessage]
) -> None:
    login = saved_login(engine, password_hash, "admin", mfa_method="email")

    client = password_step(login)
    response = submit_code(client, emailed_code(outbox))

    assert (response.status_code, response.headers["location"]) == (303, "/dashboard/admin")


def test_fr_2_8_email_code_expires(engine: Engine, password_hash: str, outbox: list[EmailMessage]) -> None:
    login = saved_login(engine, password_hash, "admin", mfa_method="email")
    client = password_step(login)
    with Session(engine) as session:
        session.execute(
            update(LoginToken)
            .where(LoginToken.login_id == login.id)
            .values(expires_at=LoginToken.expires_at - timedelta(minutes=11))
        )
        session.commit()

    response = submit_code(client, emailed_code(outbox))

    assert response.status_code == 400
    assert client.get("/dashboard/admin", follow_redirects=False).headers["location"] == "/mfa"


def test_fr_2_8_code_single_use(engine: Engine, password_hash: str) -> None:
    login, secret = app_login(engine, password_hash)
    code = pyotp.TOTP(secret).now()
    assert submit_code(password_step(login), code).status_code == 303

    reused = submit_code(password_step(login), code)

    assert reused.status_code == 400


def test_fr_2_8_email_code_single_use_and_five_tries(engine: Engine) -> None:
    login = build_login("member")
    with Session(engine) as session:
        session.add(login)
        code = issue_email_code(session, login)
        assert use_email_code(session, login, code)
        assert not use_email_code(session, login, code)

        code = issue_email_code(session, login)
        wrong = "000000" if code != "000000" else "111111"
        for _ in range(EMAIL_CODE_MAX_TRIES):
            assert not use_email_code(session, login, wrong)
        assert not use_email_code(session, login, code)
        session.rollback()


def test_fr_2_8_wrong_code_refused_counted_and_audited(engine: Engine, password_hash: str) -> None:
    login, _ = app_login(engine, password_hash)
    client = password_step(login)

    response = submit_code(client, "not-a-code")

    assert response.status_code == 400
    assert "That code is not right" in response.text
    assert "accounts.mfa" in audit_actions(engine, login)
    with Session(engine) as session:
        query = select(LoginAttempt.reason).where(LoginAttempt.login_id == login.id, ~LoginAttempt.success)
        assert list(session.scalars(query)) == ["mfa_failed"]


def test_fr_2_8_wrong_codes_lock_the_login(engine: Engine, password_hash: str) -> None:
    login, _ = app_login(engine, password_hash)
    client = password_step(login)

    for _ in range(LOCKOUT_ATTEMPTS - 1):
        assert submit_code(client, "000000").status_code == 400
    response = submit_code(client, "000000")

    assert (response.status_code, response.headers["location"]) == (303, "/login")
    assert stored_login(engine, login).locked_until is not None
    with Session(engine) as session:
        query = select(UserSession.end_reason).where(UserSession.login_id == login.id)
        assert list(session.scalars(query)) == ["locked"]


def test_fr_2_8_member_mfa_optional(engine: Engine, password_hash: str) -> None:
    member = saved_login(engine, password_hash, "member")
    client = new_client()
    response = submit_sign_in(client, member.user_id, PASSWORD)
    assert (response.status_code, response.headers["location"]) == (303, "/dashboard/member")

    turned_on = post_form(client, "/account/security/mfa-on", {}, page="/account/security")
    assert turned_on.headers["location"] == "/mfa?next=%2Faccount%2Fsecurity"
    post_form(client, "/mfa/setup", {"method": "totp", "next": "/account/security"})
    secret = decrypt_secret(stored_login(engine, member).mfa_totp_secret or "")
    done = post_form(client, "/mfa", {"code": pyotp.TOTP(secret).now(), "next": "/account/security"})
    assert done.headers["location"] == "/account/security"
    # From now on the Member's sign-in needs the code too.
    password_step(member)

    # The next time step, because the code just used for enrolment cannot be used again.
    next_code = pyotp.TOTP(secret).at(utc_now() + timedelta(seconds=30))
    turned_off = post_form(client, "/account/security/mfa-off", {"code": next_code}, page="/account/security")

    assert turned_off.headers["location"] == "/account/security?done=mfa_off"
    assert stored_login(engine, member).mfa_method is None
    assert "accounts.mfa_off" in audit_actions(engine, member)


def test_fr_2_8_member_turn_off_needs_a_right_code(engine: Engine, password_hash: str) -> None:
    secret = pyotp.random_base32()
    member = saved_login(
        engine, password_hash, "member", mfa_method="totp", mfa_totp_secret=encrypt_secret(secret)
    )
    client = password_step(member)
    submit_code(client, pyotp.TOTP(secret).now())

    response = post_form(client, "/account/security/mfa-off", {"code": "000000"}, page="/account/security")

    assert response.status_code == 400
    assert "That code is not right" in response.text
    assert stored_login(engine, member).mfa_method == "totp"


def test_p1_acc_10_totp_secret_encrypted(engine: Engine, password_hash: str) -> None:
    login = saved_login(engine, password_hash, "admin")
    client = password_step(login)

    post_form(client, "/mfa/setup", {"method": "totp"})

    stored = stored_login(engine, login).mfa_totp_secret or ""
    secret = decrypt_secret(stored)
    assert len(secret) == 32
    assert secret not in stored


def test_fr_2_8_mfa_reset_audited(sign_in: SignIn, engine: Engine, password_hash: str) -> None:
    target, _ = app_login(engine, password_hash)
    password_step(target)
    # After the target's own sign-in, because this makes every request on APP the Admin's.
    sign_in(APP, "admin")

    response = csrf_client(APP).post(f"/admin/accounts/{target.id}/reset-mfa", follow_redirects=False)

    assert response.headers["location"] == "/admin/accounts?done=mfa_reset"
    reset = stored_login(engine, target)
    assert (reset.mfa_method, reset.mfa_totp_secret) == (None, None)
    assert "accounts.mfa_reset" in audit_actions(engine, target)
    with Session(engine) as session:
        query = select(UserSession).where(UserSession.login_id == target.id, UserSession.ended_at.is_(None))
        assert session.scalars(query).first() is None


def test_fr_2_8_admin_cannot_reset_own_mfa(engine: Engine, password_hash: str) -> None:
    admin, _ = app_login(engine, password_hash)

    with Session(engine) as session, pytest.raises(AccountRuleError, match="another Admin"):
        reset_mfa(session, SYSTEM, admin, session.get_one(Login, admin.id))


def test_fr_2_8_privileged_cannot_turn_mfa_off(engine: Engine, password_hash: str) -> None:
    admin, _ = app_login(engine, password_hash)

    with Session(engine) as session, pytest.raises(AccountRuleError, match="required"):
        turn_off_member_mfa(session, admin, "000000", None)  # type: ignore[arg-type]


def test_p1_acc_10_new_code_at_most_once_a_minute(
    engine: Engine, password_hash: str, outbox: list[EmailMessage]
) -> None:
    login = saved_login(engine, password_hash, "admin", mfa_method="email")
    client = password_step(login)

    too_soon = post_form(client, "/mfa/send-code", {})
    assert too_soon.status_code == 429
    assert "less than a minute ago" in too_soon.text
    assert len(outbox) == 1

    with Session(engine) as session:
        session.execute(
            update(LoginToken)
            .where(LoginToken.login_id == login.id)
            .values(created_at=LoginToken.created_at - timedelta(seconds=61))
        )
        session.commit()
    later = post_form(client, "/mfa/send-code", {})

    assert later.status_code == 303
    assert len(outbox) == 2


def test_p1_acc_10_reset_mfa_command(engine: Engine, password_hash: str) -> None:
    admin, _ = app_login(engine, password_hash)
    password_step(admin)

    assert cli.main(["reset-mfa", "--user-id", admin.user_id.upper()]) == 0

    assert stored_login(engine, admin).mfa_method is None
    assert "accounts.mfa_reset" in audit_actions(engine, admin)
    with Session(engine) as session:
        query = select(UserSession).where(UserSession.login_id == admin.id, UserSession.ended_at.is_(None))
        assert session.scalars(query).first() is None


def test_p1_acc_10_reset_mfa_command_refuses_unknown_user() -> None:
    assert cli.main(["reset-mfa", "--user-id", "nobody.here"]) == 1
