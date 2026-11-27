"""Audit: service layer.

Business rules. Functions take `db` and `actor` explicitly, so every caller can see what a rule needs.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.audit.models import AuditEvent

# Keys whose values must never be stored, matched anywhere in a key name (security.md logging).
SENSITIVE_KEY_PARTS = ("password", "token", "secret", "csrf")
# Short names matched only whole, so harmless keys such as "postcode" or "footprint" stay.
SENSITIVE_KEYS = {"code", "otp", "mfa_code"}


@dataclass(frozen=True)
class Actor:
    """Who is acting: the login, its kind, and the session and device it acts from."""

    kind: str
    login_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    ip: str | None = None
    user_agent: str | None = None


SYSTEM = Actor(kind="system")


def record(
    db: Session,
    actor: Actor,
    action: str,
    target_type: str | None,
    target_id: str | None,
    result: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Write an audit event in the caller's transaction, so it commits or rolls back with the change."""
    # SRS 2.3: a Member login is shared, so only the session and IP show who acted.
    if actor.kind == "member" and (actor.session_id is None or actor.ip is None):
        raise ValueError("A Member action must be audited with its session ID and IP")
    event = AuditEvent(
        actor_login_id=actor.login_id,
        actor_kind=actor.kind,
        session_id=actor.session_id,
        ip=actor.ip,
        user_agent=actor.user_agent,
        action=action,
        target_type=target_type,
        target_id=target_id,
        result=result,
        details=without_sensitive_keys(details or {}),
    )
    db.add(event)
    # Flush now, so a bad action name or result fails at the caller, not at commit.
    db.flush()


def without_sensitive_keys(details: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of details without passwords, tokens, codes or secrets, at any depth."""
    clean: dict[str, Any] = {}
    for key, value in details.items():
        if _is_sensitive(key):
            continue
        if isinstance(value, dict):
            value = without_sensitive_keys(value)
        clean[key] = value
    return clean


def _is_sensitive(key: str) -> bool:
    """Return True when a details key names a secret."""
    name = key.lower()
    if name in SENSITIVE_KEYS:
        return True
    return any(part in name for part in SENSITIVE_KEY_PARTS)
