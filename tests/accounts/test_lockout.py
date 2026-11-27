"""FR-1.7: lockout after 5 consecutive failures, and a log of every attempt."""

import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.accounts.models import Login, LoginAttempt
from app.accounts.passwords import hash_password
from app.accounts.service import authenticate, is_locked
from app.audit.models import AuditEvent
from app.core.constants import LOCKOUT_ATTEMPTS
from app.core.time import utc_now
from tests.accounts.conftest import build_login

PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password
WRONG = "Wrong-Meter-2026"
IP = "10.0.0.7"
AGENT = "pytest"


@pytest.fixture(scope="module")
def password_hash() -> str:
    """Hash once per module, because argon2id is deliberately slow."""
    return hash_password(PASSWORD)


@pytest.fixture
def login(db: Session, password_hash: str) -> Login:
    saved = build_login("admin")
    saved.password_hash = password_hash
    db.add(saved)
    db.flush()
    return saved


def sign_in(db: Session, login: Login, password: str) -> Login | None:
    return authenticate(db, login.user_id, password, IP, AGENT)


def attempts(db: Session, user_id: str) -> list[LoginAttempt]:
    query = select(LoginAttempt).where(LoginAttempt.attempted_user_id == user_id).order_by(LoginAttempt.id)
    return list(db.scalars(query))


def test_fr_1_7_lockout_after_five_failures(db: Session, login: Login) -> None:
    for _ in range(LOCKOUT_ATTEMPTS - 1):
        assert sign_in(db, login, WRONG) is None
    assert not is_locked(login)

    assert sign_in(db, login, WRONG) is None
    assert is_locked(login)
    assert sign_in(db, login, PASSWORD) is None  # the right password is refused while locked

    reasons = [attempt.reason for attempt in attempts(db, login.user_id)]
    assert reasons == ["bad_password"] * LOCKOUT_ATTEMPTS + ["locked"]
    lockout = db.scalars(select(AuditEvent).where(AuditEvent.target_id == str(login.id))).one()
    assert (lockout.action, lockout.actor_kind, str(lockout.ip)) == ("accounts.lockout", "anonymous", IP)


def test_fr_1_7_lockout_expires_after_15_minutes(db: Session, login: Login) -> None:
    for _ in range(LOCKOUT_ATTEMPTS):
        sign_in(db, login, WRONG)
    assert login.locked_until is not None
    assert timedelta(minutes=14) < login.locked_until - utc_now() <= timedelta(minutes=15)

    login.locked_until = utc_now() - timedelta(seconds=1)

    assert sign_in(db, login, PASSWORD) is login


def test_fr_1_7_failed_attempts_logged(db: Session, login: Login) -> None:
    unknown = f"nobody.{uuid.uuid4().hex[:8]}"

    assert authenticate(db, unknown.upper(), PASSWORD, IP, AGENT) is None
    sign_in(db, login, WRONG)

    [unknown_attempt] = attempts(db, unknown)
    assert (unknown_attempt.login_id, unknown_attempt.reason, unknown_attempt.success) == (
        None,
        "unknown_user",
        False,
    )
    [wrong_attempt] = attempts(db, login.user_id)
    assert (wrong_attempt.login_id, wrong_attempt.reason, str(wrong_attempt.ip)) == (
        login.id,
        "bad_password",
        IP,
    )


def test_fr_1_7_success_resets_the_counter(db: Session, login: Login) -> None:
    for _ in range(LOCKOUT_ATTEMPTS - 1):
        sign_in(db, login, WRONG)
    assert login.failed_count == LOCKOUT_ATTEMPTS - 1

    assert sign_in(db, login, PASSWORD) is login

    assert login.failed_count == 0
    assert attempts(db, login.user_id)[-1].reason == "ok"


@pytest.mark.parametrize("status", ["pending", "declined", "deactivated"])
def test_p1_acc_04_inactive_login_cannot_sign_in(db: Session, login: Login, status: str) -> None:
    login.status = status

    assert sign_in(db, login, PASSWORD) is None
    assert attempts(db, login.user_id)[-1].reason == "inactive"


def test_p1_acc_04_login_without_password_cannot_sign_in(db: Session, login: Login) -> None:
    login.password_hash = None

    assert sign_in(db, login, PASSWORD) is None
    assert attempts(db, login.user_id)[-1].reason == "bad_password"


@pytest.fixture
def committed_login(engine: Engine, password_hash: str) -> Iterator[Login]:
    """A login saved for real, so parallel sessions can each see and lock it."""
    saved = build_login("admin")
    saved.password_hash = password_hash
    with Session(engine, expire_on_commit=False) as session:
        session.add(saved)
        session.commit()
    yield saved
    with Session(engine) as session:
        session.execute(delete(LoginAttempt).where(LoginAttempt.login_id == saved.id))
        session.execute(delete(Login).where(Login.id == saved.id))
        session.commit()


def test_p1_acc_04_parallel_failures_counted(engine: Engine, committed_login: Login) -> None:
    def fail_once(_: int) -> None:
        with Session(engine) as session:
            authenticate(session, committed_login.user_id, WRONG, IP, AGENT)
            session.commit()

    with ThreadPoolExecutor(max_workers=LOCKOUT_ATTEMPTS) as pool:
        list(pool.map(fail_once, range(LOCKOUT_ATTEMPTS)))

    with Session(engine) as session:
        stored = session.get_one(Login, committed_login.id)
        reasons = [attempt.reason for attempt in attempts(session, stored.user_id)]
    assert reasons == ["bad_password"] * LOCKOUT_ATTEMPTS
    assert is_locked(stored)
