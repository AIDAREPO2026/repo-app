"""Single-use secrets sent by email, such as set-password links (security.md authentication).

Only the SHA-256 of each token is stored, the same way as session tokens.
"""

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounts.models import Login, LoginToken
from app.core.constants import LINK_TOKEN_MINUTES
from app.core.sessions import hash_token, new_token
from app.core.time import utc_now


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
