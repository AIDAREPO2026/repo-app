"""Single-use secrets sent by email: set-password links and sign-in codes (security.md authentication).

Only the SHA-256 of each token or code is stored, the same way as session tokens.
"""

import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounts.models import Login, LoginToken
from app.core.constants import EMAIL_CODE_DIGITS, EMAIL_CODE_MAX_TRIES, EMAIL_CODE_MINUTES, LINK_TOKEN_MINUTES
from app.core.sessions import hash_token, new_token
from app.core.time import utc_now

EMAIL_CODE = "mfa_email_code"
EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def issue_link_token(db: Session, login: Login, purpose: str) -> str:
    """Store a new 60-minute link token for a login and return the token to put in the link."""
    token = new_token()
    db.add(
        LoginToken(
            login_id=login.id,
            purpose=purpose,
            token_hash=hash_token(token),
            expires_at=utc_now() + timedelta(minutes=LINK_TOKEN_MINUTES),
        )
    )
    db.flush()
    return token


def usable_token(db: Session, token: str, purpose: str) -> LoginToken | None:
    """Return the stored token if it exists, is for this purpose, is unused and has not expired.

    The row stays locked until the transaction ends, so two submits of one link cannot
    both use it.
    """
    query = (
        select(LoginToken)
        .where(LoginToken.token_hash == hash_token(token), LoginToken.purpose == purpose)
        .with_for_update()
    )
    found = db.scalars(query).one_or_none()
    if found is None or found.used_at is not None or found.expires_at <= utc_now():
        return None
    return found


def mark_used(found: LoginToken) -> None:
    """Use a token up, so the same link is refused next time."""
    found.used_at = utc_now()


def retire_tokens(db: Session, login: Login, *purposes: str) -> None:
    """Use up every unused token the login has for these purposes, so older links stop working."""
    query = select(LoginToken).where(
        LoginToken.login_id == login.id, LoginToken.purpose.in_(purposes), LoginToken.used_at.is_(None)
    )
    for token in db.scalars(query.with_for_update()):
        mark_used(token)


def last_issued_at(db: Session, login: Login, purpose: str) -> datetime | None:
    """Return when the login's most recent token of this kind was issued, used or not."""
    query = select(func.max(LoginToken.created_at)).where(
        LoginToken.login_id == login.id, LoginToken.purpose == purpose
    )
    return db.scalar(query)


def issue_email_code(db: Session, login: Login) -> str:
    """Store a new 6-digit, 10-minute sign-in code for a login and return it, retiring any earlier code."""
    for earlier in _unused_email_codes(db, login):
        mark_used(earlier)
    code = f"{secrets.randbelow(10**EMAIL_CODE_DIGITS):0{EMAIL_CODE_DIGITS}d}"
    issued_at = utc_now()
    db.add(
        LoginToken(
            login_id=login.id,
            purpose=EMAIL_CODE,
            token_hash=_email_code_hash(login, issued_at, code),
            expires_at=issued_at + timedelta(minutes=EMAIL_CODE_MINUTES),
            created_at=issued_at,
        )
    )
    db.flush()
    return code


def use_email_code(db: Session, login: Login, code: str) -> bool:
    """Use up the login's current sign-in code if this is it, and return whether it was.

    A wrong code counts as a try, and the 5th wrong try retires the code (FR-2.8).
    """
    current = next(iter(_unused_email_codes(db, login)), None)
    if current is None or current.expires_at <= utc_now():
        return False
    if hmac.compare_digest(current.token_hash, _email_code_hash(login, current.created_at, code)):
        mark_used(current)
        return True
    current.attempts += 1
    if current.attempts >= EMAIL_CODE_MAX_TRIES:
        mark_used(current)
    return False


def last_email_code_at(db: Session, login: Login) -> datetime | None:
    """Return when the login's most recent sign-in code was issued, used or not."""
    return last_issued_at(db, login, EMAIL_CODE)


def _unused_email_codes(db: Session, login: Login) -> list[LoginToken]:
    """Return the login's unused sign-in codes, newest first, locked until the transaction ends."""
    query = (
        select(LoginToken)
        .where(LoginToken.login_id == login.id, LoginToken.purpose == EMAIL_CODE)
        .where(LoginToken.used_at.is_(None))
        .order_by(LoginToken.created_at.desc())
        .with_for_update()
    )
    return list(db.scalars(query))


def _email_code_hash(login: Login, issued_at: datetime, code: str) -> bytes:
    """Hash a code together with its login and issue time.

    Six digits repeat often, so the code alone would clash with the unique token_hash
    column; the login and the microsecond it was issued make each stored hash distinct.
    """
    micros = (issued_at - EPOCH) // timedelta(microseconds=1)
    return hash_token(f"{login.id}:{micros}:{code}")
