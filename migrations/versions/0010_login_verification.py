"""Add who verified a Member registration, when, and why it was declined (FR-1.3, FR-1.4).

Revision ID: 0010
Revises: 0009
Created: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the verification columns. A declined login must have a reason."""
    op.add_column("login", sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("login", sa.Column("verified_by", sa.Uuid(), nullable=True))
    op.add_column("login", sa.Column("decline_reason", sa.String(1000), nullable=True))
    op.create_foreign_key(op.f("fk_login_verified_by_login"), "login", "login", ["verified_by"], ["id"])
    op.create_check_constraint(
        op.f("ck_login_declined_has_reason"),
        "login",
        "status <> 'declined' OR decline_reason IS NOT NULL",
    )


def downgrade() -> None:
    """Drop the verification columns. The audit events still record each decision."""
    op.drop_constraint(op.f("ck_login_declined_has_reason"), "login")
    op.drop_constraint(op.f("fk_login_verified_by_login"), "login")
    op.drop_column("login", "decline_reason")
    op.drop_column("login", "verified_by")
    op.drop_column("login", "verified_at")
