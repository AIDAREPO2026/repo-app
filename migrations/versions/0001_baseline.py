"""Baseline: an empty starting point that every later migration builds on.

Revision ID: 0001
Revises:
Created: 2026-11-27
"""

from collections.abc import Sequence

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Nothing to create."""


def downgrade() -> None:
    """Nothing to drop."""
