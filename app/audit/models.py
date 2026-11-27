"""Audit: models layer.

SQLAlchemy table definitions. No business rules and no event listeners here.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Identity, Index, String, Text, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, one_of

ACTOR_KINDS = ("member", "admin", "reviewer", "approver", "anonymous", "system")
RESULTS = ("success", "failure", "denied")


class AuditEvent(Base):
    """One audited action. Rows are append-only: a database trigger refuses UPDATE and DELETE."""

    __tablename__ = "audit_event"
    __table_args__ = (
        CheckConstraint(one_of("actor_kind", ACTOR_KINDS), name="actor_kind"),
        CheckConstraint(one_of("result", RESULTS), name="result"),
        # Action names are module.verb, such as settings.update.
        CheckConstraint(r"action ~ '^[a-z_]+\.[a-z_]+$'", name="action_format"),
        Index("ix_audit_event_occurred_at", "occurred_at"),
        Index("ix_audit_event_target", "target_type", "target_id"),
        Index("ix_audit_event_actor", "actor_login_id", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actor_login_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("login.id"))
    actor_kind: Mapped[str] = mapped_column(Text)
    # No foreign key, so writing the audit never depends on the session row (data-model.md).
    session_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    ip: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(500))
    action: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str | None] = mapped_column(String(32))
    target_id: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(Text)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
