"""Accounts: models layer.

SQLAlchemy table definitions. No business rules and no event listeners here.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import LOGIN_TYPES
from app.core.db import Base, one_of

LOGIN_STATUSES = ("pending", "active", "declined", "deactivated")


class Login(Base):
    """A login: one shared Member login per Discom, or a named Admin, Reviewer or Approver (FR-2.1)."""

    __tablename__ = "login"
    __table_args__ = (
        CheckConstraint(one_of("login_type", LOGIN_TYPES), name="login_type"),
        CheckConstraint(one_of("status", LOGIN_STATUSES), name="status"),
        # Stored lowercase, so the unique key is case-insensitive.
        CheckConstraint(r"user_id ~ '^[a-z0-9._-]{4,50}$'", name="user_id_format"),
        CheckConstraint(
            "login_type <> 'member' OR organisation_id IS NOT NULL", name="member_has_organisation"
        ),
        # FR-2.7: privileged accounts belong to a named person.
        CheckConstraint("login_type = 'member' OR full_name IS NOT NULL", name="privileged_has_name"),
        CheckConstraint("NOT is_alternate OR login_type = 'reviewer'", name="alternate_is_reviewer"),
        # FR-1.6, FR-2.2: one pending or active Member login per Discom. Declined or
        # deactivated logins free the Discom to register again.
        Index(
            "uq_login_one_member_per_organisation",
            "organisation_id",
            unique=True,
            postgresql_where=text("login_type = 'member' AND status IN ('pending', 'active')"),
        ),
        Index("ix_login_type_status", "login_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str] = mapped_column(String(254))
    # Null until a new privileged account sets its password (P1-ACC-09).
    password_hash: Mapped[str | None] = mapped_column(Text)
    login_type: Mapped[str] = mapped_column(Text)
    # Becomes a foreign key to organisation once that table exists (P1-ACC-01).
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    full_name: Mapped[str | None] = mapped_column(String(200))
    is_alternate: Mapped[bool] = mapped_column(Boolean, server_default="false")
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
