"""P1-ACC-06: sign-in, server-side sessions, CSRF protection and the 30-minute idle timeout."""

import hashlib
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.models import Login, UserSession
from app.accounts.passwords import hash_password
from app.accounts.router import SIGN_IN_FAILED
from app.audit.models import AuditEvent
from app.core.sessions import CSRF_HEADER, SESSION_COOKIE
from app.core.time import utc_now
from app.main import create_app
from tests.accounts.conftest import build_login, csrf_from, submit_sign_in

PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password


@pytest.fixture(scope="module")
def password_hash() -> str:
    return hash_password(PASSWORD)


@pytest.fixture
def login(engine: Engine, password_hash: str) -> Login:
    """An active Admin login, saved for real, because each request uses its own transaction."""
    saved = build_login("admin")
    saved.password_hash = password_hash
    with Session(engine, expire_on_commit=False) as session:
        session.add(saved)
        session.commit()
    return saved


@pytest.fixture
def client() -> TestClient:
    # HTTPS, because the session cookie is Secure and is not sent over plain HTTP.
    return TestClient(create_app(), base_url="https://testserver", client=("10.0.0.9", 50000))


def sessions_of(engine: Engine, login: Login) -> list[UserSession]:
    with Session(engine) as session:
        query = select(UserSession).where(UserSession.login_id == login.id).order_by(UserSession.created_at)
        return list(session.scalars(query))


def test_p1_acc_06_sign_in_opens_the_dashboard(client: TestClient, login: Login, engine: Engine) -> None:
    response = submit_sign_in(client, login.user_id.upper(), PASSWORD)

    assert response.status_code == 303
    assert response.headers["location"] == "/dashboard/admin"
    page = client.get("/dashboard/admin")
    assert page.status_code == 200
    assert "Sign out" in page.text
    with Session(engine) as session:
        actions = session.scalars(
            select(AuditEvent.action).where(AuditEvent.actor_login_id == login.id)
        ).all()
    assert actions == ["accounts.login"]


@pytest.mark.parametrize("wrong", ["wrong-password", "unknown-user"])
def test_p1_acc_06_failed_sign_in_shows_one_generic_message(
    client: TestClient, login: Login, wrong: str
) -> None:
    user_id = "nobody.at.all" if wrong == "unknown-user" else login.user_id
    password = PASSWORD if wrong == "unknown-user" else "Wrong-Meter-2026"

    response = submit_sign_in(client, user_id, password)

    assert response.status_code == 200
    assert SIGN_IN_FAILED in response.text
    assert SESSION_COOKIE not in response.cookies


def test_p1_acc_06_csrf_required_on_post(client: TestClient, login: Login) -> None:
    form = {"user_id": login.user_id, "password": PASSWORD}
    assert client.post("/login", data=form).status_code == 403
    assert client.post("/login", data={**form, "csrf_token": "forged"}).status_code == 403

    submit_sign_in(client, login.user_id, PASSWORD)
    assert client.post("/logout", follow_redirects=False).status_code == 403
    session_token = csrf_from(client.get("/dashboard/admin"))
    response = client.post("/logout", headers={CSRF_HEADER: session_token}, follow_redirects=False)
    assert response.status_code == 303


def test_p1_acc_06_token_rotates_on_login(client: TestClient, login: Login, engine: Engine) -> None:
    submit_sign_in(client, login.user_id, PASSWORD)
    first_token = client.cookies[SESSION_COOKIE]

    submit_sign_in(client, login.user_id, PASSWORD)
    second_token = client.cookies[SESSION_COOKIE]

    assert first_token != second_token
    first, second = sessions_of(engine, login)
    assert (first.end_reason, second.end_reason) == ("replaced", None)
    client.cookies.set(SESSION_COOKIE, first_token)
    assert client.get("/dashboard/admin", follow_redirects=False).status_code == 303


def test_p1_acc_06_cookie_flags(client: TestClient, login: Login) -> None:
    visitor_cookie = client.get("/login").headers["set-cookie"]
    session_cookie = submit_sign_in(client, login.user_id, PASSWORD).headers["set-cookie"]

    for header in (visitor_cookie, session_cookie):
        flags = [part.strip().lower() for part in header.split(";")]
        assert {"httponly", "secure", "samesite=lax", "path=/"} <= set(flags)
        assert not any(flag.startswith("domain") for flag in flags)
    assert session_cookie.startswith(f"{SESSION_COOKIE}=")


def test_p1_acc_06_token_stored_hashed(client: TestClient, login: Login, engine: Engine) -> None:
    submit_sign_in(client, login.user_id, PASSWORD)
    token = client.cookies[SESSION_COOKIE]

    [stored] = sessions_of(engine, login)

    assert stored.token_hash == hashlib.sha256(token.encode()).digest()
    assert token not in (stored.csrf_token, stored.user_agent)
    assert len(token) >= 43  # 32 random bytes, URL-safe base64


def set_last_seen(engine: Engine, login: Login, minutes_ago: float) -> None:
    with Session(engine) as session:
        moment = utc_now() - timedelta(minutes=minutes_ago)
        session.execute(
            update(UserSession).where(UserSession.login_id == login.id).values(last_seen_at=moment)
        )
        session.commit()


def test_fr_1_7_idle_session_ends_after_30_minutes(client: TestClient, login: Login, engine: Engine) -> None:
    submit_sign_in(client, login.user_id, PASSWORD)
    set_last_seen(engine, login, 29)
    assert client.get("/dashboard/admin").status_code == 200

    set_last_seen(engine, login, 31)
    response = client.get("/dashboard/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/dashboard/admin"
    [ended] = sessions_of(engine, login)
    assert ended.end_reason == "idle"


def test_p1_acc_06_last_seen_written_at_most_once_a_minute(
    client: TestClient, login: Login, engine: Engine
) -> None:
    submit_sign_in(client, login.user_id, PASSWORD)
    set_last_seen(engine, login, 0.2)
    before = sessions_of(engine, login)[0].last_seen_at
    client.get("/dashboard/admin")
    assert sessions_of(engine, login)[0].last_seen_at == before

    set_last_seen(engine, login, 2)
    client.get("/dashboard/admin")
    assert utc_now() - sessions_of(engine, login)[0].last_seen_at < timedelta(seconds=10)


def test_p1_acc_06_sign_out_ends_session_at_once(client: TestClient, login: Login, engine: Engine) -> None:
    submit_sign_in(client, login.user_id, PASSWORD)
    token = client.cookies[SESSION_COOKIE]
    csrf = csrf_from(client.get("/dashboard/admin"))

    response = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)

    assert response.headers["location"] == "/login"
    [ended] = sessions_of(engine, login)
    assert ended.end_reason == "logout"
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/dashboard/admin", follow_redirects=False).status_code == 303


@pytest.mark.parametrize(
    ("next_path", "expected"),
    [
        ("/dashboard/admin", "/dashboard/admin"),
        ("//evil.example/page", "/dashboard/admin"),
        ("/\\evil.example", "/dashboard/admin"),
        ("https://evil.example", "/dashboard/admin"),
        ("", "/dashboard/admin"),
    ],
)
def test_p1_acc_06_next_never_leaves_the_site(
    client: TestClient, login: Login, next_path: str, expected: str
) -> None:
    response = submit_sign_in(client, login.user_id, PASSWORD, next_path)

    assert response.headers["location"] == expected


def test_p1_acc_06_signed_in_user_skips_the_sign_in_page(client: TestClient, login: Login) -> None:
    submit_sign_in(client, login.user_id, PASSWORD)

    response = client.get("/login", follow_redirects=False)

    assert (response.status_code, response.headers["location"]) == (303, "/dashboard/admin")
