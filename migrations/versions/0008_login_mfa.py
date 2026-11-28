"""Add the MFA columns to login, and the "locked" session end reason (FR-2.8).

Revision ID: 0008
Revises: 0007
Created: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the MFA method, the encrypted authenticator secret, the last used time step and the enrol time."""
    op.add_column("login", sa.Column("mfa_method", sa.Text(), nullable=True))
    op.add_column("login", sa.Column("mfa_totp_secret", sa.Text(), nullable=True))
    op.add_column("login", sa.Column("mfa_totp_last_step", sa.BigInteger(), nullable=True))
    op.add_column("login", sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(op.f("ck_login_mfa_method"), "login", "mfa_method IN ('totp', 'email')")
    op.create_check_constraint(
        op.f("ck_login_totp_has_secret"),
        "login",
        "mfa_method IS DISTINCT FROM 'totp' OR mfa_totp_secret IS NOT NULL",
    )

    # A session ended because too many wrong codes locked the login.
    _set_end_reasons("'logout', 'idle', 'replaced', 'admin', 'password_reset', 'locked'")


def downgrade() -> None:
    """Drop the MFA columns. Everyone enrolled must enrol again after an upgrade."""
    op.execute("UPDATE user_session SET end_reason = 'admin' WHERE end_reason = 'locked'")
    _set_end_reasons("'logout', 'idle', 'replaced', 'admin', 'password_reset'")
    op.drop_constraint(op.f("ck_login_totp_has_secret"), "login")
    op.drop_constraint(op.f("ck_login_mfa_method"), "login")
    op.drop_column("login", "mfa_enrolled_at")
    op.drop_column("login", "mfa_totp_last_step")
    op.drop_column("login", "mfa_totp_secret")
    op.drop_column("login", "mfa_method")


def _set_end_reasons(reasons: str) -> None:
    """Replace the allowed session end reasons."""
    op.drop_constraint(op.f("ck_user_session_end_reason"), "user_session")
    op.create_check_constraint(
        op.f("ck_user_session_end_reason"), "user_session", f"end_reason IN ({reasons})"
    )
