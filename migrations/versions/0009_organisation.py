"""Add organisation, the Discom master list, and link Member logins to it (FR-1.6).

Revision ID: 0009
Revises: 0008
Created: 2026-11-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from migrations.grants import grant_to_app_role

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create organisation and make login.organisation_id a foreign key to it."""
    op.create_table(
        "organisation",
        sa.Column("id", postgresql.UUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("email_domain", sa.String(length=253), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'inactive')", name=op.f("ck_organisation_status")),
        sa.CheckConstraint(
            "email_domain = lower(email_domain)", name=op.f("ck_organisation_email_domain_lowercase")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organisation")),
        sa.UniqueConstraint("email_domain", name=op.f("uq_organisation_email_domain")),
    )
    op.create_index("uq_organisation_name", "organisation", [sa.text("lower(name)")], unique=True)
    # Discoms are deactivated, never deleted (SRS 6.3).
    grant_to_app_role("organisation", "SELECT, INSERT, UPDATE")
    # Member logins made before this table existed point at Discoms that are not listed yet.
    # Each gets an inactive placeholder, so the key can be added and the login kept, but it
    # cannot sign in until an Admin gives the Discom its real name and domain.
    op.execute("""
        INSERT INTO organisation (id, name, email_domain, status)
        SELECT DISTINCT organisation_id,
               'Unlisted Discom ' || organisation_id,
               organisation_id || '.unlisted.invalid',
               'inactive'
        FROM login
        WHERE organisation_id IS NOT NULL
    """)
    op.create_foreign_key(
        op.f("fk_login_organisation_id_organisation"), "login", "organisation", ["organisation_id"], ["id"]
    )


def downgrade() -> None:
    """Drop the foreign key and organisation. Member logins keep their organisation IDs."""
    op.drop_constraint(op.f("fk_login_organisation_id_organisation"), "login", type_="foreignkey")
    op.drop_index("uq_organisation_name", table_name="organisation")
    op.drop_table("organisation")
