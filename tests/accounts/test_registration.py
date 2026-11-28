"""P1-ACC-02: a Discom requests its Member login through the public form (FR-1.1, FR-1.2, FR-1.6, D-11)."""

import re
import uuid
from email.message import EmailMessage
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.models import Login, Organisation
from app.accounts.passwords import verify_password
from app.accounts.service import CAPTCHA_FAILED, DISCOM_TAKEN, WRONG_REGISTRATION_CODE, suggest_user_ids
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


def visitor() -> TestClient:
    """A visitor on HTTPS, so the registration cookie comes back, with a valid CSRF token."""
    client = csrf_client(APP)
    client.base_url = "https://testserver"
    return client


def start(client: TestClient, discom: Organisation, captcha: str | None = None, email: str = "") -> Response:
    form = {
        "organisation_id": str(discom.id),
        "email": email or f"Officer.{uuid.uuid4().hex[:8]}@{discom.email_domain}",
        "altcha": solved_captcha(client) if captcha is None else captcha,
    }
    return client.post("/register", data=form, follow_redirects=False)


def code_in(message: EmailMessage) -> str:
    match = re.search(r"code is (\d{6})", message.get_content())
    assert match, message.get_content()
    return match.group(1)


def enter_code(client: TestClient, code: str) -> Response:
    return client.post("/register/code", data={"code": code}, follow_redirects=False)


def verify(client: TestClient, discom: Organisation, outbox: list[EmailMessage], email: str = "") -> None:
    """Take a visitor through steps 1 and 2."""
    assert start(client, discom, email=email).headers["location"] == "/register/code"
    assert enter_code(client, code_in(outbox[-1])).headers["location"] == "/register/account"


def finish(client: TestClient, **changes: str) -> Response:
    form = {
        "user_id": f"discom.{uuid.uuid4().hex[:10]}",
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    }
    return client.post("/register/account", data=form | changes, follow_redirects=False)


def member_logins(engine: Engine, discom: Organisation) -> list[Login]:
    with Session(engine) as session:
        return list(session.scalars(select(Login).where(Login.organisation_id == discom.id)))


def audits(engine: Engine, action: str, discom: Organisation) -> list[dict[str, Any]]:
    with Session(engine) as session:
        query = (
            select(AuditEvent)
            .where(AuditEvent.action == action)
            .where(AuditEvent.details["organisation_id"].astext == str(discom.id))
            .order_by(AuditEvent.id)
        )
        return [{"result": event.result} | event.details for event in session.scalars(query)]


def test_fr_1_1_registration_creates_pending_login(engine: Engine, outbox: list[EmailMessage]) -> None:
    client, discom = visitor(), new_discom(engine)
    email = f"Officer@{discom.email_domain}"
    verify(client, discom, outbox, email=email)
    user_id = f"discom.{uuid.uuid4().hex[:10]}"

    response = finish(client, user_id=user_id)

    assert response.headers["location"] == "/register/sent"
    assert "sent to ITPED for verification" in client.get("/register/sent").text
    [login] = member_logins(engine, discom)
    assert (login.login_type, login.status, login.user_id) == ("member", "pending", user_id)
    assert login.email == email.lower()
    assert login.password_hash is not None
    assert verify_password(login.password_hash, PASSWORD)
    assert audits(engine, "accounts.register", discom)[0]["result"] == "success"
    # The verification is used up.
    assert finish(client).headers["location"] == "/register"


def test_fr_1_2_captcha_required(engine: Engine, outbox: list[EmailMessage]) -> None:
    client = visitor()
    answer = solved_captcha(client)
    assert start(client, new_discom(engine), captcha=answer).status_code == 303
    sent = len(outbox)

    missing = start(client, new_discom(engine), captcha="")
    replay = start(client, new_discom(engine), captcha=answer)

    for response in (missing, replay):
        assert response.status_code == 400
        assert CAPTCHA_FAILED in response.text
    assert len(outbox) == sent


def test_d11_only_the_discoms_domain_is_sent_a_code(engine: Engine, outbox: list[EmailMessage]) -> None:
    discom = new_discom(engine)
    good = start(visitor(), discom)
    good_page = TestClient(APP, base_url="https://testserver", cookies=good.cookies).get("/register/code")
    outbox.clear()

    for domain in ["gmail.com", f"mail.{discom.email_domain}", f"{discom.email_domain}.example"]:
        client = visitor()
        response = start(client, discom, email=f"officer@{domain}")
        # Spec security: the same answer as a good request, so domains cannot be probed.
        assert (response.status_code, response.headers["location"]) == (303, "/register/code")
        assert "drr_register" in response.cookies
        wrong = enter_code(client, "000000")
        assert WRONG_REGISTRATION_CODE in wrong.text

    assert good_page.status_code == 200
    assert outbox == []
    reasons = [event.get("reason") for event in audits(engine, "accounts.register_code", discom)]
    assert reasons == [None, "email_domain", "email_domain", "email_domain"]


def test_p1_acc_02_five_wrong_codes_end_the_code(engine: Engine, outbox: list[EmailMessage]) -> None:
    client, discom = visitor(), new_discom(engine)
    start(client, discom)
    code = code_in(outbox[-1])
    wrong = "111111" if code != "111111" else "222222"

    for _ in range(5):
        assert enter_code(client, wrong).status_code == 400

    assert enter_code(client, code).status_code == 400


def test_p1_acc_02_one_code_a_minute_for_an_address(engine: Engine, outbox: list[EmailMessage]) -> None:
    discom = new_discom(engine)
    email = f"officer@{discom.email_domain}"
    client = visitor()
    start(client, discom, email=email)

    second = start(client, discom, email=email)

    assert second.headers["location"] == "/register/code"
    assert len(outbox) == 1
    # The code already sent still works for the newer request.
    assert enter_code(client, code_in(outbox[0])).headers["location"] == "/register/account"


def test_p1_acc_02_later_steps_need_a_proved_email(engine: Engine, outbox: list[EmailMessage]) -> None:
    client, discom = visitor(), new_discom(engine)
    assert client.get("/register/account", follow_redirects=False).headers["location"] == "/register"
    assert client.get("/register/user-id", params={"value": "someone"}).status_code == 404
    assert finish(client).headers["location"] == "/register"

    start(client, discom)  # a code is waiting, but has not been entered

    assert client.get("/register/user-id", params={"value": "someone"}).status_code == 404
    assert finish(client).headers["location"] == "/register"
    assert member_logins(engine, discom) == []


def test_p1_acc_02_suggestions_and_checks_know_taken_ids(engine: Engine, outbox: list[EmailMessage]) -> None:
    client, discom = visitor(), new_discom(engine)
    person = f"asha{uuid.uuid4().hex[:6]}"
    existing = build_login("member")
    existing.user_id = person
    saved(engine, existing)
    verify(client, discom, outbox, email=f"{person}@{discom.email_domain}")

    page = client.get("/register/account").text
    offered = re.findall(r"data-use-user-id>([^<]+)<", page)

    assert len(offered) == 3
    assert person not in offered

    def state(value: str) -> str:
        return client.get("/register/user-id", params={"value": value}).json()["state"]

    assert state(person.upper()) == "taken"
    assert state(offered[0]) == "free"
    assert state("a b") == "invalid"
    with Session(engine) as session:
        assert suggest_user_ids(session, "Power (NPCX)", f"{person}@x.example")[0] != person


def test_p1_acc_02_user_id_checks_are_limited(engine: Engine, outbox: list[EmailMessage]) -> None:
    client, discom = visitor(), new_discom(engine)
    verify(client, discom, outbox)

    def ask() -> str:
        return client.get("/register/user-id", params={"value": "somebody"}).json()["state"]

    states = [ask() for _ in range(31)]

    assert states[:30] == ["free"] * 30
    assert states[30] == "limit"


def test_p1_acc_02_taken_user_id_is_said_once_proved(engine: Engine, outbox: list[EmailMessage]) -> None:
    client, discom = visitor(), new_discom(engine)
    existing = build_login("member")
    saved(engine, existing)
    verify(client, discom, outbox)

    response = finish(client, user_id=existing.user_id)

    assert response.status_code == 400
    assert "That User ID is taken" in response.text
    assert member_logins(engine, discom) == []


def test_fr_1_6_duplicate_registration_refused(engine: Engine, outbox: list[EmailMessage]) -> None:
    discom = new_discom(engine)
    saved(engine, build_login("member", status="pending", organisation=discom))

    response = start(visitor(), discom)

    assert response.status_code == 400
    assert DISCOM_TAKEN in response.text
    assert len(member_logins(engine, discom)) == 1
    assert audits(engine, "accounts.register_code", discom)[-1]["reason"] == "discom_has_login"
    assert outbox == []


def test_p1_acc_02_format_problems_shown_by_field(engine: Engine, outbox: list[EmailMessage]) -> None:
    client, discom = visitor(), new_discom(engine)
    first = start(client, discom, email="not-an-email")
    assert first.status_code == 400
    assert 'id="email-error"' in first.text
    verify(client, discom, outbox)

    response = finish(client, user_id="ab", confirm_password="Other-2026!x")  # noqa: S106 - test value

    assert response.status_code == 400
    assert 'id="user_id-error"' in response.text
    assert "The two passwords do not match." in response.text
    assert PASSWORD not in response.text
    assert member_logins(engine, discom) == []


def test_p1_acc_02_inactive_discom_cannot_register(engine: Engine) -> None:
    inactive = new_discom(engine, status="inactive")

    response = start(visitor(), inactive)

    assert response.status_code == 400
    assert "Choose your Discom from the list." in response.text


def test_p1_acc_02_privacy_notice_shown(engine: Engine, outbox: list[EmailMessage]) -> None:
    active = new_discom(engine)
    inactive = new_discom(engine, status="inactive")
    client = visitor()

    first = client.get("/register").text
    verify(client, active, outbox)
    last = client.get("/register/account").text

    for page in (first, last):
        assert "Privacy notice" in page
        assert "What we collect" in page
    assert active.name in first
    assert inactive.name not in first


def test_fr_1_6_a_discom_listed_with_a_public_domain_gets_no_code(
    engine: Engine, outbox: list[EmailMessage]
) -> None:
    # Listed straight in the database, as one saved before public domains were blocked would be.
    discom = build_organisation()
    discom.email_domain = "rediffmail.com"
    saved(engine, discom)

    response = start(visitor(), discom)

    assert response.headers["location"] == "/register/code"
    assert outbox == []
    assert audits(engine, "accounts.register_code", discom)[0]["reason"] == "email_domain"
