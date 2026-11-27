import uuid

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.audit.models import AuditEvent
from app.audit.service import SYSTEM, Actor, record
from app.core.settings_store import set_setting


def audit_one(db: Session) -> AuditEvent:
    """Write one audit event and return it."""
    record(db, SYSTEM, "tests.write", "test", str(uuid.uuid4()), "success")
    return db.scalars(select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1)).one()


def events_for(db: Session, target_id: str) -> list[AuditEvent]:
    return list(db.scalars(select(AuditEvent).where(AuditEvent.target_id == target_id)))


def test_fr_12_1_audit_rows_cannot_be_updated(db: Session) -> None:
    event = audit_one(db)

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(update(AuditEvent).where(AuditEvent.id == event.id).values(result="failure"))


def test_fr_12_1_audit_rows_cannot_be_deleted(db: Session) -> None:
    event = audit_one(db)

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(delete(AuditEvent).where(AuditEvent.id == event.id))


def test_fr_12_1_audit_table_cannot_be_truncated(db: Session) -> None:
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("TRUNCATE audit_event"))


def test_fr_12_1_app_role_may_only_insert_and_select(db: Session) -> None:
    rights = {
        right: db.scalar(text(f"SELECT has_table_privilege('aida_app', 'audit_event', '{right}')"))
        for right in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
    }

    assert rights == {"SELECT": True, "INSERT": True, "UPDATE": False, "DELETE": False, "TRUNCATE": False}


def test_fr_4_6_audit_rolls_back_with_change(db: Session) -> None:
    set_setting(db, "newly_added_days", 30, actor=SYSTEM)
    assert len(events_for(db, "newly_added_days")) == 1

    db.rollback()

    assert events_for(db, "newly_added_days") == []


def test_p1_aud_01_setting_change_records_old_and_new(db: Session) -> None:
    set_setting(db, "newly_added_days", 30, actor=SYSTEM)
    set_setting(db, "newly_added_days", 20, actor=SYSTEM)

    latest = events_for(db, "newly_added_days")[-1]
    assert (latest.action, latest.target_type, latest.result) == ("settings.update", "setting", "success")
    assert latest.details == {"old": 30, "new": 20}


def test_p1_aud_01_sensitive_keys_dropped(db: Session) -> None:
    details = {
        "password": "x",
        "new_password": "x",
        "reset_token": "x",
        "totp_secret": "x",
        "csrf_token": "x",
        "code": "123456",
        "otp": "123456",
        "user_id": "discom.one",
        "postcode": "110001",
        "nested": {"session_token": "x", "reason": "kept"},
    }

    record(db, SYSTEM, "tests.write", "test", "sensitive", "success", details)

    stored = events_for(db, "sensitive")[0].details
    assert stored == {"user_id": "discom.one", "postcode": "110001", "nested": {"reason": "kept"}}


def test_p1_aud_01_member_action_needs_session_and_ip(db: Session) -> None:
    shared_login = Actor(kind="member")

    with pytest.raises(ValueError, match="session ID and IP"):
        record(db, shared_login, "content.submit", "content", "x", "success")

    traced = Actor(kind="member", session_id=uuid.uuid4(), ip="10.0.0.7")
    record(db, traced, "content.submit", "content", "traced", "success")
    assert str(events_for(db, "traced")[0].ip) == "10.0.0.7"


@pytest.mark.parametrize(("action", "result"), [("NoDot", "success"), ("settings.update", "maybe")])
def test_p1_aud_01_bad_action_or_result_refused(db: Session, action: str, result: str) -> None:
    with pytest.raises(DBAPIError):
        record(db, SYSTEM, action, None, None, result)
