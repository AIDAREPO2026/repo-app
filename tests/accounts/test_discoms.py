"""P1-ACC-01: the Discom master list, its Admin screens, CSV import and the inactive-Discom rule (FR-1.6)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.discom_names import DISCOM_NAME_SUGGESTIONS
from app.accounts.models import LoginAttempt, Organisation, UserSession
from app.accounts.passwords import hash_password
from app.accounts.router import SIGN_IN_FAILED
from app.accounts.service import TEST_DISCOMS, AccountRuleError, seed_test_discoms
from app.audit.models import AuditEvent
from app.main import create_app
from tests.accounts.conftest import (
    CLIENT,
    SignIn,
    build_login,
    build_organisation,
    csrf_client,
    submit_sign_in,
)

APP = create_app()
PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password


def unique() -> str:
    return uuid.uuid4().hex[:10]


def saved_discom(engine: Engine, status: str = "active") -> Organisation:
    discom = build_organisation(status)
    with Session(engine, expire_on_commit=False) as session:
        session.add(discom)
        session.commit()
    return discom


def stored_discom(engine: Engine, discom_id: uuid.UUID) -> Organisation:
    with Session(engine) as session:
        return session.get_one(Organisation, discom_id)


def discom_by_domain(engine: Engine, email_domain: str) -> Organisation | None:
    with Session(engine) as session:
        return session.scalars(
            select(Organisation).where(Organisation.email_domain == email_domain)
        ).one_or_none()


def audit_actions(engine: Engine, discom_id: uuid.UUID) -> list[str]:
    with Session(engine) as session:
        query = (
            select(AuditEvent.action).where(AuditEvent.target_id == str(discom_id)).order_by(AuditEvent.id)
        )
        return list(session.scalars(query))


def upload(client: TestClient, csv_text: str | bytes) -> object:
    content = csv_text.encode() if isinstance(csv_text, str) else csv_text
    return client.post("/admin/discoms/import/preview", files={"file": ("discoms.csv", content, "text/csv")})


def test_fr_1_6_master_list_crud(sign_in: SignIn, engine: Engine) -> None:
    sign_in(APP, "admin")
    client = csrf_client(APP)
    domain = f"{unique()}.discom.example"

    added = client.post(
        "/admin/discoms",
        data={"name": " Grid Discom ", "email_domain": f"@{domain.upper()}"},
        follow_redirects=False,
    )
    assert added.headers["location"] == "/admin/discoms?done=added"
    discom = discom_by_domain(engine, domain)
    assert discom is not None
    assert discom.name == "Grid Discom"
    assert "Grid Discom" in client.get("/admin/discoms").text

    new_domain = f"{unique()}.discom.example"
    client.post(
        f"/admin/discoms/{discom.id}/edit", data={"name": "Grid Discom Ltd", "email_domain": new_domain}
    )
    edited = stored_discom(engine, discom.id)
    assert (edited.name, edited.email_domain) == ("Grid Discom Ltd", new_domain)

    client.post(f"/admin/discoms/{discom.id}/deactivate")
    assert stored_discom(engine, discom.id).status == "inactive"
    client.post(f"/admin/discoms/{discom.id}/reactivate")
    assert stored_discom(engine, discom.id).status == "active"

    assert audit_actions(engine, discom.id) == [
        "accounts.discom_add",
        "accounts.discom_edit",
        "accounts.discom_deactivate",
        "accounts.discom_reactivate",
    ]


def test_fr_1_6_duplicate_domain_refused(sign_in: SignIn, engine: Engine) -> None:
    sign_in(APP, "admin")
    client = csrf_client(APP)
    listed = saved_discom(engine)

    same_domain = client.post(
        "/admin/discoms", data={"name": f"Other {unique()}", "email_domain": listed.email_domain}
    )
    same_name = client.post(
        "/admin/discoms", data={"name": listed.name.upper(), "email_domain": f"{unique()}.discom.example"}
    )
    other = saved_discom(engine)
    edit_to_taken = client.post(
        f"/admin/discoms/{other.id}/edit", data={"name": other.name, "email_domain": listed.email_domain}
    )

    assert same_domain.status_code == 400
    assert "email domain is already listed" in same_domain.text
    assert same_name.status_code == 400
    assert "name is already listed" in same_name.text
    assert edit_to_taken.status_code == 400
    assert stored_discom(engine, other.id).email_domain == other.email_domain


def test_fr_1_6_duplicate_refused_by_database(db: Session) -> None:
    listed = build_organisation()
    db.add(listed)
    db.flush()

    db.add(Organisation(name=listed.name.lower(), email_domain=f"{unique()}.discom.example"))
    with pytest.raises(IntegrityError, match="uq_organisation_name"):
        db.flush()


def test_fr_1_6_invalid_domain_refused(sign_in: SignIn) -> None:
    sign_in(APP, "admin")

    response = csrf_client(APP).post(
        "/admin/discoms", data={"name": f"Bad {unique()}", "email_domain": "not a domain"}
    )

    assert response.status_code == 422


def test_fr_1_6_inactive_discom_blocked(sign_in: SignIn, engine: Engine) -> None:
    member = build_login("member")
    member.password_hash = hash_password(PASSWORD)
    with Session(engine, expire_on_commit=False) as session:
        session.add(member)
        session.commit()
    member_client = TestClient(APP, base_url="https://testserver", client=CLIENT)
    assert submit_sign_in(member_client, member.user_id, PASSWORD).headers["location"] == "/dashboard/member"

    sign_in(APP, "admin")
    csrf_client(APP).post(f"/admin/discoms/{member.organisation_id}/deactivate")
    APP.dependency_overrides.clear()

    with Session(engine) as session:
        open_sessions = select(UserSession).where(
            UserSession.login_id == member.id, UserSession.ended_at.is_(None)
        )
        assert session.scalars(open_sessions).first() is None
    refused = submit_sign_in(
        TestClient(APP, base_url="https://testserver", client=CLIENT), member.user_id, PASSWORD
    )
    assert SIGN_IN_FAILED in refused.text
    with Session(engine) as session:
        reasons = (
            select(LoginAttempt.reason).where(LoginAttempt.login_id == member.id).order_by(LoginAttempt.id)
        )
        assert list(session.scalars(reasons)) == ["ok", "inactive"]


def test_fr_1_6_csv_import_preview_then_save(sign_in: SignIn, engine: Engine) -> None:
    sign_in(APP, "admin")
    client = csrf_client(APP)
    listed = saved_discom(engine)
    taken = saved_discom(engine)
    new_one, new_two = f"{unique()}.discom.example", f"{unique()}.discom.example"
    csv_text = "\n".join(
        [
            "Name,Email_Domain",
            f"New Discom {new_one},{new_one}",
            f"{listed.name},{listed.email_domain}",
            f"Clash {unique()},{taken.email_domain}",
            f"Broken {unique()},not a domain",
            f"Repeat {unique()},{new_one}",
            f"Second New {new_two},{new_two.upper()}",
        ]
    )

    preview = upload(client, csv_text)

    assert preview.status_code == 200
    assert preview.text.count("Will be added") == 2
    assert "Already listed" in preview.text
    assert f"already listed for {taken.name}" in preview.text
    assert "not a valid domain" in preview.text
    assert "Same name or domain as line 2" in preview.text
    # Nothing is saved by the preview.
    assert discom_by_domain(engine, new_one) is None

    saved = client.post("/admin/discoms/import", data={"csv_text": csv_text}, follow_redirects=False)

    assert saved.headers["location"] == "/admin/discoms?added=2"
    assert discom_by_domain(engine, new_one) is not None
    assert discom_by_domain(engine, new_two) is not None


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("name,domain\nA,a.example", "must name the columns"),
        ("name,email_domain\n", "no Discoms"),
        (b"name,email_domain\n\xff\xfe,x", "CSV UTF-8"),
    ],
)
def test_p1_acc_01_unreadable_csv_refused(sign_in: SignIn, content: str | bytes, message: str) -> None:
    sign_in(APP, "admin")

    response = upload(csrf_client(APP), content)

    assert response.status_code == 400
    assert message in response.text


def test_p1_acc_01_seed_test_discoms(engine: Engine) -> None:
    with Session(engine) as session:
        seed_test_discoms(session, "staging")
        session.commit()
        assert seed_test_discoms(session, "staging") == 0

    for form in TEST_DISCOMS:
        assert discom_by_domain(engine, form.email_domain) is not None


def test_p1_acc_01_seed_refused_in_production(db: Session) -> None:
    with pytest.raises(AccountRuleError, match="not production"):
        seed_test_discoms(db, "production")


def test_fr_1_6_public_mail_domain_refused_on_add_edit_and_import(sign_in: SignIn, engine: Engine) -> None:
    sign_in(APP, "admin")
    client = csrf_client(APP)
    listed = saved_discom(engine)

    added = client.post("/admin/discoms", data={"name": f"Free {unique()}", "email_domain": "@GMail.com"})
    edited = client.post(
        f"/admin/discoms/{listed.id}/edit", data={"name": listed.name, "email_domain": "yahoo.co.in"}
    )
    preview = upload(client, f"name,email_domain\nFree {unique()},outlook.com")

    assert added.status_code == 400
    assert "Anyone can get an address" in added.text
    assert discom_by_domain(engine, "gmail.com") is None
    assert edited.status_code == 400
    assert stored_discom(engine, listed.id).email_domain == listed.email_domain
    assert "Anyone can get an address" in preview.text
    assert "Will be added" not in preview.text


def test_fr_1_6_add_form_suggests_names_not_already_listed(sign_in: SignIn, engine: Engine) -> None:
    sign_in(APP, "admin")
    first, second = DISCOM_NAME_SUGGESTIONS[0], DISCOM_NAME_SUGGESTIONS[1]
    with Session(engine) as session:
        session.add(Organisation(name=first, email_domain=f"{unique()}.discom.example"))
        session.commit()

    page = csrf_client(APP).get("/admin/discoms").text

    assert 'list="add-name-list"' in page
    assert f'<option value="{second}">' in page
    assert f'<option value="{first}">' not in page
