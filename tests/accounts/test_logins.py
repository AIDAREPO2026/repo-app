import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.accounts.models import Login
from app.core.constants import LOGIN_TYPES
from tests.accounts.conftest import build_login, build_organisation


def save(db: Session, login: Login) -> None:
    db.add(login)
    db.flush()


def test_fr_2_1_only_four_login_types(db: Session) -> None:
    assert LOGIN_TYPES == ("member", "admin", "reviewer", "approver")
    for login_type in LOGIN_TYPES:
        save(db, build_login(login_type))

    with pytest.raises(IntegrityError, match="ck_login_login_type"):
        save(db, build_login("visitor"))


def test_fr_2_2_one_member_login_per_discom(db: Session) -> None:
    discom = build_organisation()
    save(db, build_login("member", status="active", organisation=discom))

    with pytest.raises(IntegrityError, match="uq_login_one_member_per_organisation"):
        save(db, build_login("member", status="pending", organisation=discom))


def test_fr_2_2_declined_login_frees_the_discom(db: Session) -> None:
    discom = build_organisation()
    save(db, build_login("member", status="declined", organisation=discom))
    save(db, build_login("member", status="deactivated", organisation=discom))

    save(db, build_login("member", status="pending", organisation=discom))


@pytest.mark.parametrize(
    ("changes", "constraint"),
    [
        ({"user_id": "Mixed.Case"}, "ck_login_user_id_format"),
        ({"user_id": "abc"}, "ck_login_user_id_format"),
        ({"user_id": "has space"}, "ck_login_user_id_format"),
        ({"login_type": "member", "organisation_id": None}, "ck_login_member_has_organisation"),
        ({"full_name": None}, "ck_login_privileged_has_name"),
        ({"is_alternate": True}, "ck_login_alternate_is_reviewer"),
        ({"status": "suspended"}, "ck_login_status"),
    ],
)
def test_p1_acc_08_login_rules_enforced_by_database(
    db: Session, changes: dict[str, object], constraint: str
) -> None:
    login = build_login("admin")
    for name, value in changes.items():
        setattr(login, name, value)

    with pytest.raises(IntegrityError, match=constraint):
        save(db, login)


def test_p1_acc_08_user_id_is_unique(db: Session) -> None:
    first = build_login("admin")
    save(db, first)
    second = build_login("admin")
    second.user_id = first.user_id

    with pytest.raises(IntegrityError, match="uq_login_user_id"):
        save(db, second)
