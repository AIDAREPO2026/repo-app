"""P1-ACC-07: a Member login works on at most five devices (FR-2.3, D-10)."""

import re
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from email.message import EmailMessage

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.device_names import device_name
from app.accounts.models import Login, UserSession
from app.accounts.passwords import hash_password
from app.audit.models import AuditEvent
from app.core.sessions import hash_token, new_token
from app.core.settings_store import AppSetting
from app.core.time import utc_now
from app.main import create_app
from tests.accounts.conftest import CLIENT, SignIn, build_login, csrf_client, csrf_from, submit_sign_in

APP = create_app()
PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password
REFUSED = "already signed in on 5 devices"


@pytest.fixture(autouse=True)
def default_policy(engine: Engine) -> Iterator[None]:
    """Start and end each test on the default policy, which other tests share."""

    def clear() -> None:
        with Session(engine) as session:
            session.execute(delete(AppSetting).where(AppSetting.key == "sixth_session_policy"))
            session.commit()

    clear()
    yield
    clear()


def member(engine: Engine) -> Login:
    login = build_login("member")
    login.password_hash = hash_password(PASSWORD)
    with Session(engine, expire_on_commit=False) as session:
        session.add(login)
        session.commit()
    return login


def new_device() -> TestClient:
    return TestClient(APP, base_url="https://testserver", client=CLIENT)


def signed_in_device(login: Login) -> TestClient:
    client = new_device()
    assert submit_sign_in(client, login.user_id, PASSWORD).status_code == 303
    return client


def works(client: TestClient) -> bool:
    return client.get("/dashboard/member", follow_redirects=False).status_code == 200


def sessions_of(engine: Engine, login: Login) -> list[UserSession]:
    query = select(UserSession).where(UserSession.login_id == login.id).order_by(UserSession.created_at)
    with Session(engine) as session:
        return list(session.scalars(query))


def live(engine: Engine, login: Login) -> int:
    return len([item for item in sessions_of(engine, login) if item.ended_at is None])


def use_policy(policy: str, sign_in: SignIn) -> None:
    sign_in(APP, "admin")
    response = csrf_client(APP).post("/admin/sign-in-rules", data={"policy": policy}, follow_redirects=False)
    assert response.status_code == 303
    APP.dependency_overrides.clear()


def test_fr_2_3_five_sessions_allowed(engine: Engine) -> None:
    login = member(engine)

    devices = [signed_in_device(login) for _ in range(5)]

    assert all(works(device) for device in devices)


def test_fr_2_3_sixth_blocked(engine: Engine) -> None:
    login = member(engine)
    devices = [signed_in_device(login) for _ in range(5)]

    response = submit_sign_in(new_device(), login.user_id, PASSWORD)

    assert response.status_code == 200
    assert REFUSED in response.text
    assert all(works(device) for device in devices)
    assert live(engine, login) == 5
    with Session(engine) as session:
        refusals = session.scalars(
            select(AuditEvent.details).where(
                AuditEvent.target_id == str(login.id), AuditEvent.result == "denied"
            )
        ).all()
    assert refusals == [{"reason": "device_limit"}]


def test_fr_2_3_sixth_ends_oldest(engine: Engine, sign_in: SignIn) -> None:
    use_policy("end_oldest", sign_in)
    login = member(engine)
    devices = [signed_in_device(login) for _ in range(5)]

    sixth = signed_in_device(login)

    assert not works(devices[0])
    assert all(works(device) for device in [*devices[1:], sixth])
    oldest = sessions_of(engine, login)[0]
    assert oldest.end_reason == "replaced"
    with Session(engine) as session:
        ended = session.scalars(select(AuditEvent.action).where(AuditEvent.target_id == str(oldest.id)))
        assert ended.all() == ["accounts.session_end"]


def test_fr_2_3_parallel_logins_never_exceed_five(engine: Engine) -> None:
    login = member(engine)
    devices = [new_device() for _ in range(8)]

    with ThreadPoolExecutor(max_workers=len(devices)) as pool:
        answers = list(pool.map(lambda d: submit_sign_in(d, login.user_id, PASSWORD), devices))

    assert sorted(answer.status_code for answer in answers) == [200] * 3 + [303] * 5
    assert live(engine, login) == 5


def test_p1_acc_07_an_idle_device_frees_its_place(engine: Engine) -> None:
    login = member(engine)
    for _ in range(5):
        signed_in_device(login)
    with Session(engine) as session:
        unused = utc_now() - timedelta(minutes=31)
        session.execute(
            update(UserSession).where(UserSession.login_id == login.id).values(last_seen_at=unused)
        )
        session.commit()

    signed_in_device(login)

    assert live(engine, login) == 1
    assert [item.end_reason for item in sessions_of(engine, login)][:5] == ["idle"] * 5


def test_p1_acc_07_signing_in_again_on_a_device_takes_no_new_place(engine: Engine) -> None:
    login = member(engine)
    devices = [signed_in_device(login) for _ in range(5)]
    token = csrf_from(devices[0].get("/account/devices"))
    form = {"user_id": login.user_id, "password": PASSWORD, "csrf_token": token}

    response = devices[0].post("/login", data=form, follow_redirects=False)

    assert response.status_code == 303
    assert live(engine, login) == 5


def test_p1_acc_07_a_member_signs_out_its_own_devices_only(engine: Engine) -> None:
    login, other = member(engine), member(engine)
    mine, second = signed_in_device(login), signed_in_device(login)
    theirs = signed_in_device(other)
    page = mine.get("/account/devices")
    assert page.text.count('/sign-out"') == 2 and "This device" in page.text
    token = csrf_from(page)
    own_id, second_id = (item.id for item in sessions_of(engine, login))
    their_id = sessions_of(engine, other)[0].id

    def sign_out(session_id: uuid.UUID) -> int:
        url = f"/account/devices/{session_id}/sign-out"
        return mine.post(url, data={"csrf_token": token}, follow_redirects=False).status_code

    assert sign_out(their_id) == 404
    assert works(theirs)
    assert sign_out(second_id) == 303
    assert not works(second) and works(mine)
    assert sign_out(own_id) == 303
    assert not works(mine)


@pytest.mark.parametrize("login_type", ["member", "reviewer", "approver"])
def test_p1_acc_07_only_admin_sets_the_policy(login_type: str, sign_in: SignIn) -> None:
    sign_in(APP, login_type)
    client = csrf_client(APP)

    assert client.get("/admin/sign-in-rules").status_code == 403
    assert client.post("/admin/sign-in-rules", data={"policy": "end_oldest"}).status_code == 403


def test_p1_acc_07_devices_are_named_from_the_browser() -> None:
    chrome = "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
    iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Version/18.0 Safari/604.1"

    assert device_name(chrome) == "Chrome on Windows"
    assert device_name(iphone) == "Safari on iPhone"
    assert device_name("") == "Unknown browser"


def occupy(engine: Engine, login: Login, places: int) -> None:
    """Add signed-in sessions directly, standing for other devices."""
    with Session(engine) as session:
        for _ in range(places):
            token_hash = hash_token(new_token())
            session.add(
                UserSession(token_hash=token_hash, login_id=login.id, csrf_token=new_token(), ip="127.0.0.1")
            )
        session.commit()


def two_step_member(engine: Engine) -> Login:
    login = member(engine)
    with Session(engine) as session:
        session.execute(update(Login).where(Login.id == login.id).values(mfa_method="email"))
        session.commit()
    return login


def test_p1_acc_07_a_full_login_is_refused_before_a_code_is_asked_for(
    engine: Engine, outbox: list[EmailMessage]
) -> None:
    login = two_step_member(engine)
    occupy(engine, login, 5)

    response = submit_sign_in(new_device(), login.user_id, PASSWORD)

    assert REFUSED in response.text
    assert outbox == []


def test_p1_acc_07_the_last_place_can_go_while_the_code_is_typed(
    engine: Engine, outbox: list[EmailMessage]
) -> None:
    login = two_step_member(engine)
    occupy(engine, login, 4)
    client = new_device()
    assert submit_sign_in(client, login.user_id, PASSWORD).headers["location"].startswith("/mfa")
    code = re.search(r"\b\d{6}\b", outbox[-1].get_content())
    assert code
    occupy(engine, login, 1)
    form = {"code": code.group(0), "method": "email", "csrf_token": csrf_from(client.get("/mfa"))}

    response = client.post("/mfa", data=form, follow_redirects=False)

    assert response.headers["location"] == "/login?done=devices_full"
    assert REFUSED in client.get(response.headers["location"]).text
    assert not works(client)
    assert len([item for item in sessions_of(engine, login) if item.ended_at is None]) == 5
