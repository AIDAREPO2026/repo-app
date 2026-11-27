"""Add login_token and the privileged account rules on login (FR-2.7).

Revision ID: 0007
Revises: 0006
Created: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.grants import grant_to_app_role

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create login_token, and add the one-Approver, one-Reviewer-per-role and one-email-per-login rules."""
    op.create_table(
        "login_token",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("login_id", postgresql.UUID(), nullable=False),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("token_hash", postgresql.BYTEA(), nullable=False),
        sa.Column("attempts", sa.SmallInteger(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "purpose IN ('set_password', 'reset_password', 'mfa_email_code', 'confirm_extra_email')",
            name=op.f("ck_login_token_purpose"),
        ),
        sa.ForeignKeyConstraint(["login_id"], ["login.id"], name=op.f("fk_login_token_login_id_login")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_token")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_login_token_token_hash")),
    )
    op.create_index(
        "ix_login_token_unused",
        "login_token",
        ["login_id", "purpose"],
        postgresql_where=sa.text("used_at IS NULL"),
    )
    # Tokens are marked used, never deleted, so a reused link can be told from a wrong one.
    grant_to_app_role("login_token", "SELECT, INSERT, UPDATE", "login_token_id_seq")
    op.create_index(
        "uq_login_one_active_approver",
        "login",
        ["login_type"],
        unique=True,
        postgresql_where=sa.text("login_type = 'approver' AND status = 'active'"),
    )
    op.create_index(
        "uq_login_current_email",
        "login",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("status IN ('pending', 'active')"),
    )
    op.execute(
        "ALTER TABLE login ADD CONSTRAINT xc_login_one_reviewer_per_role "
        "EXCLUDE USING btree (is_alternate WITH =) "
        "WHERE (login_type = 'reviewer' AND status = 'active') DEFERRABLE INITIALLY DEFERRED"
    )


def downgrade() -> None:
    """Drop the rules and login_token. Unused set-password links stop working."""
    op.drop_constraint("xc_login_one_reviewer_per_role", "login")
    op.drop_index("uq_login_current_email", table_name="login")
    op.drop_index("uq_login_one_active_approver", table_name="login")
    op.drop_table("login_token")
