"""Add the user_session table for server-side sessions (FR-1.7, SRS 2.3).

Revision ID: 0006
Revises: 0005
Created: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.grants import grant_to_app_role

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create user_session."""
    op.create_table(
        "user_session",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("token_hash", postgresql.BYTEA(), nullable=False),
        sa.Column("login_id", postgresql.UUID(), nullable=False),
        sa.Column("csrf_token", sa.String(length=64), nullable=False),
        sa.Column("mfa_pending", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.Text(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=False),
        sa.Column("user_agent", sa.String(length=500), server_default="", nullable=False),
        sa.CheckConstraint(
            "end_reason IN ('logout', 'idle', 'replaced', 'admin', 'password_reset')",
            name=op.f("ck_user_session_end_reason"),
        ),
        sa.CheckConstraint(
            "(ended_at IS NULL) = (end_reason IS NULL)", name=op.f("ck_user_session_ended_with_reason")
        ),
        sa.ForeignKeyConstraint(["login_id"], ["login.id"], name=op.f("fk_user_session_login_id_login")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_session")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_session_token_hash")),
    )
    op.create_index(
        "ix_user_session_active", "user_session", ["login_id"], postgresql_where=sa.text("ended_at IS NULL")
    )
    # Sessions are ended, never deleted, because audit events refer to them.
    grant_to_app_role("user_session", "SELECT, INSERT, UPDATE")


def downgrade() -> None:
    """Drop user_session. Everyone is signed out."""
    op.drop_table("user_session")
