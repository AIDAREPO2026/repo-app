"""Add the append-only audit_event table, and make app_setting.updated_by a login UUID.

Revision ID: 0003
Revises: 0002
Created: 2026-11-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# FR-12.1: audit rows can never change. The trigger holds even for the table owner.
BLOCK_CHANGES = """
CREATE FUNCTION audit_event_block_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_event is append-only: % refused', TG_OP;
END;
$$;
CREATE TRIGGER audit_event_no_update_delete
    BEFORE UPDATE OR DELETE ON audit_event
    FOR EACH ROW EXECUTE FUNCTION audit_event_block_change();
CREATE TRIGGER audit_event_no_truncate
    BEFORE TRUNCATE ON audit_event
    FOR EACH STATEMENT EXECUTE FUNCTION audit_event_block_change();
"""

# The application role may only add and read audit rows (data-model.md grants). Servers
# create the role; locally and in CI it may not exist, so the grant is skipped there.
GRANT_APP_ROLE = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aida_app') THEN
        GRANT SELECT, INSERT ON audit_event TO aida_app;
        GRANT USAGE ON SEQUENCE audit_event_id_seq TO aida_app;
    END IF;
END;
$$;
"""


def upgrade() -> None:
    """Create audit_event with its checks, indexes, trigger and grant."""
    op.create_table(
        "audit_event",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("actor_login_id", postgresql.UUID(), nullable=True),
        sa.Column("actor_kind", sa.Text(), nullable=False),
        sa.Column("session_id", postgresql.UUID(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False),
        sa.CheckConstraint(
            "actor_kind IN ('member', 'admin', 'reviewer', 'approver', 'anonymous', 'system')",
            name=op.f("ck_audit_event_actor_kind"),
        ),
        sa.CheckConstraint("result IN ('success', 'failure', 'denied')", name=op.f("ck_audit_event_result")),
        sa.CheckConstraint(r"action ~ '^[a-z_]+\.[a-z_]+$'", name=op.f("ck_audit_event_action_format")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_event")),
    )
    op.create_index("ix_audit_event_occurred_at", "audit_event", ["occurred_at"])
    op.create_index("ix_audit_event_target", "audit_event", ["target_type", "target_id"])
    op.create_index("ix_audit_event_actor", "audit_event", ["actor_login_id", "occurred_at"])
    op.execute(BLOCK_CHANGES)
    op.execute(GRANT_APP_ROLE)
    # No login has existed yet, so there are no values to convert.
    op.alter_column("app_setting", "updated_by", type_=postgresql.UUID(), postgresql_using="NULL")


def downgrade() -> None:
    """Drop audit_event and its trigger function. Dropping the table discards the audit trail."""
    op.alter_column("app_setting", "updated_by", type_=sa.Integer(), postgresql_using="NULL")
    op.drop_table("audit_event")
    op.execute("DROP FUNCTION audit_event_block_change()")
