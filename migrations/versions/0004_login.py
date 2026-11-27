"""Add the login table, and point audit and settings actors at it.

Revision ID: 0004
Revises: 0003
Created: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.grants import grant_to_app_role

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create login with its rules, and add the foreign keys that wait for it."""
    op.create_table(
        "login",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("user_id", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("login_type", sa.Text(), nullable=False),
        sa.Column("organisation_id", postgresql.UUID(), nullable=True),
        sa.Column("full_name", sa.String(length=200), nullable=True),
        sa.Column("is_alternate", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "login_type IN ('member', 'admin', 'reviewer', 'approver')", name=op.f("ck_login_login_type")
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'declined', 'deactivated')", name=op.f("ck_login_status")
        ),
        sa.CheckConstraint(r"user_id ~ '^[a-z0-9._-]{4,50}$'", name=op.f("ck_login_user_id_format")),
        sa.CheckConstraint(
            "login_type <> 'member' OR organisation_id IS NOT NULL",
            name=op.f("ck_login_member_has_organisation"),
        ),
        sa.CheckConstraint(
            "login_type = 'member' OR full_name IS NOT NULL", name=op.f("ck_login_privileged_has_name")
        ),
        sa.CheckConstraint(
            "NOT is_alternate OR login_type = 'reviewer'", name=op.f("ck_login_alternate_is_reviewer")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login")),
        sa.UniqueConstraint("user_id", name=op.f("uq_login_user_id")),
    )
    op.create_index(
        "uq_login_one_member_per_organisation",
        "login",
        ["organisation_id"],
        unique=True,
        postgresql_where=sa.text("login_type = 'member' AND status IN ('pending', 'active')"),
    )
    op.create_index("ix_login_type_status", "login", ["login_type", "status"])
    grant_to_app_role("login", "SELECT, INSERT, UPDATE")
    op.create_foreign_key(
        op.f("fk_audit_event_actor_login_id_login"), "audit_event", "login", ["actor_login_id"], ["id"]
    )
    op.create_foreign_key(
        op.f("fk_app_setting_updated_by_login"), "app_setting", "login", ["updated_by"], ["id"]
    )


def downgrade() -> None:
    """Drop the foreign keys, then login."""
    op.drop_constraint(op.f("fk_app_setting_updated_by_login"), "app_setting", type_="foreignkey")
    op.drop_constraint(op.f("fk_audit_event_actor_login_id_login"), "audit_event", type_="foreignkey")
    op.drop_table("login")
