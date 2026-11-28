"""P1-ACC-02: a Discom requests its Member login through the public form (FR-1.1, FR-1.2, FR-1.6, D-11)."""

import uuid
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.models import Login, Organisation
from app.accounts.passwords import verify_password
from app.accounts.service import CAPTCHA_FAILED, DISCOM_TAKEN
from app.audit.models import AuditEvent
from app.main import create_app
from tests.accounts.conftest import build_login, build_organisation, csrf_client
from tests.core.test_captcha import solve

APP = create_app()
PASSWORD = "Grid-Meter-2026!"  # noqa: S105 - a test value, not a real password


def saved(engine: Engine, *rows: object) -> None:
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(rows)
        session.commit()


def new_discom(engine: Engine, status: str = "active") -> Organisation:
    discom = build_organisation(status)
    saved(engine, discom)
    return discom


def solved_captcha(client: TestClient) -> str:
    challenge = client.get("/captcha/challenge")
    assert challenge.headers["cache-control"] == "no-store"
    return solve(challenge.json())


def request_form(discom: Organisation, captcha: str, **changes: str) -> dict[str, str]:
    user_id = f"discom.{uuid.uuid4().hex[:10]}"
    form = {
        "organisation_id": str(discom.id),
        "email": f"Officer@{discom.email_domain}",
        "user_id": user_id,
        "password": PASSWORD,
        "confirm_password": PASSWORD,
        "altcha": captcha,
    }
    return form | changes


def register(client: TestClient, form: dict[str, str]) -> Response:
    return client.post("/register", data=form, follow_redirects=False)


def member_logins(engine: Engine, discom: Organisation) -> list[Login]:
    with Session(engine) as session:
        return list(session.scalars(select(Login).where(Login.organisation_id == discom.id)))


def registration_audits(engine: Engine, discom: Organisation) -> list[dict[str, Any]]:
    with Session(engine) as session:
        query = (
            select(AuditEvent)
            .where(AuditEvent.action == "accounts.register")
            .where(AuditEvent.details["organisation_id"].astext == str(discom.id))
            .order_by(AuditEvent.id)
        )
        return [{"result": event.result} | event.details for event in session.scalars(query)]


def test_fr_1_1_registration_creates_pending_login(engine: Engine) -> None:
    client = csrf_client(APP)
    discom = new_discom(engine)
    form = request_form(discom, solved_captcha(client))

    response = register(client, form)

    assert response.headers["location"] == "/register/sent"
    assert "sent to ITPED for verification" in client.get("/register/sent").text
    [login] = member_logins(engine, discom)
    assert (login.login_type, login.status, login.user_id) == ("member", "pending", form["user_id"])
    assert login.email == f"officer@{discom.email_domain}"
    assert login.password_hash is not None
    assert verify_password(login.password_hash, PASSWORD)
    assert registration_audits(engine, discom)[0]["result"] == "success"


def test_fr_1_2_captcha_required(engine: Engine) -> None:
    client = csrf_client(APP)
    unsolved = new_discom(engine)
    replayed = new_discom(engine)
    answer = solved_captcha(client)
    assert register(client, request_form(new_discom(engine), answer)).status_code == 303

    missing = register(client, request_form(unsolved, ""))
    replay = register(client, request_form(replayed, answer))

    for response in (missing, replay):
        assert response.status_code == 400
        assert CAPTCHA_FAILED in response.text
    assert member_logins(engine, unsolved) == []
    assert member_logins(engine, replayed) == []


def test_fr_1_6_duplicate_registration_refused(engine: Engine) -> None:
    client = csrf_client(APP)
    discom = new_discom(engine)
    saved(engine, build_login("member", status="pending", organisation=discom))

    response = register(client, request_form(discom, solved_captcha(client)))

    assert response.status_code == 400
    assert DISCOM_TAKEN in response.text
    assert len(member_logins(engine, discom)) == 1
    assert registration_audits(engine, discom)[-1]["reason"] == "discom_has_login"


def test_d11_email_domain_must_match(engine: Engine) -> None:
    client = csrf_client(APP)
    discom = new_discom(engine)
    other_domains = ["gmail.com", f"mail.{discom.email_domain}", f"{discom.email_domain}.example"]

    for domain in other_domains:
        form = request_form(discom, solved_captcha(client), email=f"officer@{domain}")
        # Spec security: the same answer as a good request, so domains cannot be probed.
        assert register(client, form).headers["location"] == "/register/sent"

    assert member_logins(engine, discom) == []
    reasons = [event["reason"] for event in registration_audits(engine, discom)]
    assert reasons == ["email_domain"] * len(other_domains)


def test_p1_acc_02_taken_user_id_answers_as_sent(engine: Engine) -> None:
    client = csrf_client(APP)
    existing = build_login("member")
    saved(engine, existing)
    discom = new_discom(engine)

    response = register(client, request_form(discom, solved_captcha(client), user_id=existing.user_id))

    assert response.headers["location"] == "/register/sent"
    assert member_logins(engine, discom) == []
    assert registration_audits(engine, discom)[-1]["reason"] == "user_id_taken"


def test_p1_acc_02_format_problems_shown_by_field(engine: Engine) -> None:
    client = csrf_client(APP)
    discom = new_discom(engine)
    form = request_form(
        discom,
        solved_captcha(client),
        email="not-an-email",
        user_id="ab",
        confirm_password="Other-2026!x",  # noqa: S106 - test value
    )

    response = register(client, form)

    assert response.status_code == 400
    assert 'id="email-error"' in response.text
    assert 'id="user_id-error"' in response.text
    assert "The two passwords do not match." in response.text
    assert PASSWORD not in response.text
    assert member_logins(engine, discom) == []


def test_p1_acc_02_inactive_discom_cannot_register(engine: Engine) -> None:
    client = csrf_client(APP)
    inactive = new_discom(engine, status="inactive")

    response = register(client, request_form(inactive, solved_captcha(client)))

    assert response.status_code == 400
    assert "Choose your Discom from the list." in response.text
    assert member_logins(engine, inactive) == []


def test_p1_acc_02_privacy_notice_shown(engine: Engine) -> None:
    active = new_discom(engine)
    inactive = new_discom(engine, status="inactive")

    page = TestClient(APP).get("/register").text

    assert "Privacy notice" in page
    assert "What we collect" in page
    assert active.name in page
    assert inactive.name not in page


def test_fr_1_6_registration_refused_for_a_discom_listed_with_a_public_domain(engine: Engine) -> None:
    # Listed straight in the database, as one saved before public domains were blocked would be.
    discom = build_organisation()
    discom.email_domain = "rediffmail.com"
    saved(engine, discom)
    client = csrf_client(APP)

    response = register(client, request_form(discom, solved_captcha(client)))

    # The same answer as a good request, so the form does not say why (D-11).
    assert response.headers["location"] == "/register/sent"
    assert member_logins(engine, discom) == []
    assert registration_audits(engine, discom)[0]["reason"] == "email_domain"
