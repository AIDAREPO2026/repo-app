"""P1-ACC-02: words nobody may use in a User ID, the tricks refused, and the Admin page for them."""

import uuid
from email.message import EmailMessage

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts import user_id_rules
from app.accounts.schemas import PrivilegedAccountForm, ReservedWordForm
from app.accounts.service import (
    USER_ID_NOT_ALLOWED,
    AccountRuleError,
    create_privileged_account,
    free_word,
    reserve_word,
    reserved_words,
    suggest_user_ids,
)
from app.accounts.user_id_rules import DEFAULT_ANYWHERE, DEFAULT_PARTS, is_reserved, shape_problem
from app.audit.service import SYSTEM
from app.main import create_app
from tests.accounts.conftest import SignIn, build_organisation, csrf_client
from tests.accounts.test_registration import finish, new_discom, saved, verify, visitor

APP = create_app()


def reserved(user_id: str) -> bool:
    return is_reserved(user_id, list(DEFAULT_ANYWHERE), list(DEFAULT_PARTS))


@pytest.mark.parametrize(
    "user_id",
    [
        "admin", "msedcl.admin2", "a.d-m_in", "4dm1n", "adm1n.rao", "addmiin", "admins", "itped.help",
        "root123", "r00t.user", "www.msedcl", "msedcl_api", "ftp2.rao", "msedcl.support", "http.proxy",
        "a.p.i", "msedcl.portal", "aaida", "no-reply",
    ],
)  # fmt: skip
def test_p1_acc_02_reserved_words_are_seen_through_disguises(user_id: str) -> None:
    assert reserved(user_id), user_id


@pytest.mark.parametrize(
    "user_id",
    ["asha.rao", "msedcl.office", "supportive.rao", "apiwala", "appu.nair", "zaida.khan", "nodal.office"],
)
def test_p1_acc_02_honest_ids_are_allowed(user_id: str) -> None:
    assert not reserved(user_id), user_id
    assert shape_problem(user_id) == ""


@pytest.mark.parametrize("user_id", ["1asha", "asha.", "asha..rao", "a1234", "msedcl.co.in", "report.php"])
def test_p1_acc_02_shapes_that_are_refused(user_id: str) -> None:
    assert shape_problem(user_id)


def test_p1_acc_02_every_default_word_is_stored_plain() -> None:
    for word in [*DEFAULT_ANYWHERE, *DEFAULT_PARTS]:
        assert word == user_id_rules.plain_word(word)
    assert all(len(word) >= 4 for word in DEFAULT_ANYWHERE)


def test_p1_acc_02_admin_words_apply_and_can_be_freed(db: Session) -> None:
    word = "zeb" + "".join("abcdefghij"[int(c, 16) % 10] for c in uuid.uuid4().hex[:6])
    form = ReservedWordForm(word=f" {word.upper()}. ", where="parts")
    discom = build_organisation()
    discom.name = "Grid Power"
    db.add(discom)
    db.flush()

    reserve_word(db, SYSTEM, form)

    assert word in reserved_words(db, "parts")
    assert word not in suggest_user_ids(db, discom, f"{word}@x.example")
    with pytest.raises(AccountRuleError, match="already reserved"):
        reserve_word(db, SYSTEM, form)
    free_word(db, SYSTEM, ReservedWordForm(word=word, where="parts"))
    assert word in suggest_user_ids(db, discom, f"{word}@x.example")


def test_p1_acc_02_a_short_word_cannot_be_refused_anywhere(db: Session) -> None:
    with pytest.raises(AccountRuleError, match="4 to 30"):
        reserve_word(db, SYSTEM, ReservedWordForm(word="an", where="anywhere"))


def test_p1_acc_02_registration_refuses_reserved_and_another_discoms_code(
    engine: Engine, outbox: list[EmailMessage]
) -> None:
    other = build_organisation()
    other.name = "Other Power (QZVX)"
    saved(engine, other)
    client, discom = visitor(), new_discom(engine)
    verify(client, discom, outbox)

    for user_id in ("msedcl.admin", "qzvx.office"):
        response = finish(client, user_id=user_id)
        assert response.status_code == 400
        assert USER_ID_NOT_ALLOWED in response.text
        state = client.get("/register/user-id", params={"value": user_id}).json()["state"]
        assert state == "reserved"


def test_p1_acc_02_staff_accounts_follow_the_same_rules(db: Session, outbox: list[EmailMessage]) -> None:
    form = PrivilegedAccountForm(
        login_type="admin", full_name="Asha Rao", email="asha.r@itped.example", user_id="super.admin"
    )

    with pytest.raises(AccountRuleError, match=USER_ID_NOT_ALLOWED):
        create_privileged_account(db, SYSTEM, form, "https://portal.example")


def test_p1_acc_02_admin_page_adds_removes_and_refuses_others(sign_in: SignIn) -> None:
    sign_in(APP, "admin")
    client = csrf_client(APP)
    word = "qkwy" + "".join("abcdefghij"[int(c, 16) % 10] for c in uuid.uuid4().hex[:4])

    added = client.post("/admin/reserved-ids", data={"word": word, "where": "parts"}, follow_redirects=False)
    listed = client.get("/admin/reserved-ids").text
    removed = client.post(
        "/admin/reserved-ids/remove", data={"word": word, "where": "parts"}, follow_redirects=False
    )

    assert added.headers["location"] == "/admin/reserved-ids?done=added"
    assert f'value="{word}"' in listed
    assert removed.headers["location"] == "/admin/reserved-ids?done=removed"
    assert f'value="{word}"' not in client.get("/admin/reserved-ids").text

    APP.dependency_overrides.clear()
    sign_in(APP, "reviewer")
    refused = csrf_client(APP).post("/admin/reserved-ids", data={"word": "abcd", "where": "parts"})
    assert refused.status_code == 403
