"""Add lockout fields to login, and the login_attempt table (FR-1.7).

Revision ID: 0005
Revises: 0004
Created: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.grants import grant_to_app_role

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add failed_count and locked_until to login, and create login_attempt."""
    op.add_column("login", sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False))
    op.add_column("login", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(op.f("ck_login_failed_count_not_negative"), "login", "failed_count >= 0")
    op.create_table(
        "login_attempt",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("attempted_user_id", sa.String(length=254), nullable=False),
        sa.Column("login_id", postgresql.UUID(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("user_agent", sa.String(length=500), server_default="", nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "reason IN ('ok', 'unknown_user', 'bad_password', 'locked', 'inactive', 'mfa_failed')",
            name=op.f("ck_login_attempt_reason"),
        ),
        sa.ForeignKeyConstraint(["login_id"], ["login.id"], name=op.f("fk_login_attempt_login_id_login")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_attempt")),
    )
    op.create_index("ix_login_attempt_login", "login_attempt", ["login_id", "at"])
    op.create_index("ix_login_attempt_ip", "login_attempt", ["ip", "at"])
    # A log: the application only adds and reads attempts.
    grant_to_app_role("login_attempt", "SELECT, INSERT", sequence="login_attempt_id_seq")


def downgrade() -> None:
    """Drop login_attempt and the lockout fields."""
    op.drop_table("login_attempt")
    op.drop_constraint(op.f("ck_login_failed_count_not_negative"), "login", type_="check")
    op.drop_column("login", "locked_until")
    op.drop_column("login", "failed_count")
