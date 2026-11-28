"""Accounts: models layer.

SQLAlchemy table definitions. No business rules and no event listeners here.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import BYTEA, INET, UUID, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import LOGIN_TYPES
from app.core.db import Base, one_of

LOGIN_STATUSES = ("pending", "active", "declined", "deactivated")
SESSION_END_REASONS = ("logout", "idle", "replaced", "admin", "password_reset", "locked")
ATTEMPT_REASONS = ("ok", "unknown_user", "bad_password", "locked", "inactive", "mfa_failed")
TOKEN_PURPOSES = ("set_password", "reset_password", "mfa_email_code", "confirm_extra_email")
MFA_METHODS = ("totp", "email")


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
        CheckConstraint("failed_count >= 0", name="failed_count_not_negative"),
        CheckConstraint(one_of("mfa_method", MFA_METHODS), name="mfa_method"),
        CheckConstraint(
            "mfa_method IS DISTINCT FROM 'totp' OR mfa_totp_secret IS NOT NULL", name="totp_has_secret"
        ),
        # FR-1.6, FR-2.2: one pending or active Member login per Discom. Declined or
        # deactivated logins free the Discom to register again.
        Index(
            "uq_login_one_member_per_organisation",
            "organisation_id",
            unique=True,
            postgresql_where=text("login_type = 'member' AND status IN ('pending', 'active')"),
        ),
        Index("ix_login_type_status", "login_type", "status"),
        # FR-2.7: one active Approver, the Centre Director.
        Index(
            "uq_login_one_active_approver",
            "login_type",
            unique=True,
            postgresql_where=text("login_type = 'approver' AND status = 'active'"),
        ),
        # FR-2.7: no shared privileged accounts. P1-ACC-05 also relies on it to find a login by email.
        Index(
            "uq_login_current_email",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("status IN ('pending', 'active')"),
        ),
        # FR-2.7: one active primary and one active alternate Reviewer. An exclusion
        # constraint rather than a unique index, because only a constraint can be deferred,
        # and swapping primary and alternate passes through a moment with two of one kind.
        ExcludeConstraint(
            ("is_alternate", "="),
            name="xc_login_one_reviewer_per_role",
            where=text("login_type = 'reviewer' AND status = 'active'"),
            deferrable=True,
            initially="DEFERRED",
        ),
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
    # FR-1.7: consecutive failed sign-ins, and the end of a lockout.
    failed_count: Mapped[int] = mapped_column(Integer, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # FR-2.8: null means MFA is off, which only a Member may keep. A secret with no method is
    # an authenticator app enrolment that has not been confirmed with a code yet.
    mfa_method: Mapped[str | None] = mapped_column(Text)
    # Fernet-encrypted (app.accounts.mfa). Never logged.
    mfa_totp_secret: Mapped[str | None] = mapped_column(Text)
    # The last authenticator time step accepted, so the same code cannot be used twice.
    mfa_totp_last_step: Mapped[int | None] = mapped_column(BigInteger)
    mfa_enrolled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LoginAttempt(Base):
    """One sign-in attempt, kept for lockout alerts and investigation (FR-1.7). Never holds the password."""

    __tablename__ = "login_attempt"
    __table_args__ = (
        CheckConstraint(one_of("reason", ATTEMPT_REASONS), name="reason"),
        Index("ix_login_attempt_login", "login_id", "at"),
        Index("ix_login_attempt_ip", "ip", "at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # As typed, so attempts on unknown User IDs are kept too.
    attempted_user_id: Mapped[str] = mapped_column(String(254))
    login_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("login.id"))
    ip: Mapped[str] = mapped_column(INET)
    user_agent: Mapped[str] = mapped_column(String(500), server_default="")
    success: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(Text)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSession(Base):
    """One signed-in browser. The cookie holds the token; only its SHA-256 hash is stored."""

    __tablename__ = "user_session"
    __table_args__ = (
        CheckConstraint(one_of("end_reason", SESSION_END_REASONS), name="end_reason"),
        CheckConstraint("(ended_at IS NULL) = (end_reason IS NULL)", name="ended_with_reason"),
        # FR-2.3: active sessions are counted per login (P1-ACC-07).
        Index("ix_user_session_active", "login_id", postgresql_where=text("ended_at IS NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    token_hash: Mapped[bytes] = mapped_column(BYTEA, unique=True)
    login_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("login.id"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    mfa_pending: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_reason: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str] = mapped_column(INET)
    user_agent: Mapped[str] = mapped_column(String(500), server_default="")


class LoginToken(Base):
    """A single-use secret sent by email, such as a set-password link. Only its SHA-256 hash is stored."""

    __tablename__ = "login_token"
    __table_args__ = (
        CheckConstraint(one_of("purpose", TOKEN_PURPOSES), name="purpose"),
        Index("ix_login_token_unused", "login_id", "purpose", postgresql_where=text("used_at IS NULL")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    login_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("login.id"))
    purpose: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[bytes] = mapped_column(BYTEA, unique=True)
    # Wrong tries, for email codes (P1-ACC-10). Links do not use it.
    attempts: Mapped[int] = mapped_column(SmallInteger, server_default="0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
