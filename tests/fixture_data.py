"""Fictional Discoms and logins for tests and staging (P0-QA-02). Never real people or data.

Emails use the reserved `.example` domain (RFC 2606), so no message can reach anyone.
Passwords and MFA secrets are not kept here: they come from environment variables in CI
secrets, so the repository never holds a working credential. Later tasks load these into
the database once the tables exist (P0-ARC-01, P1-ACC-08).
"""

from typing import NamedTuple

from app.accounts.service import TEST_DISCOMS


class FixtureDiscom(NamedTuple):
    """A fictional Discom with the email domain its staff use (D-11)."""

    name: str
    code: str
    email_domain: str


class FixtureLogin(NamedTuple):
    """One login. Member logins belong to a Discom; ITPED logins have none."""

    user_id: str
    login_type: str
    email: str
    discom_code: str | None
    is_alternate: bool


# The same three Discoms `python -m app.accounts.cli seed-test-discoms` adds (P1-ACC-01).
NORTH, SOUTH, EAST = TEST_DISCOMS
DISCOMS = [
    FixtureDiscom(NORTH.name, "NTD", NORTH.email_domain),
    FixtureDiscom(SOUTH.name, "STD", SOUTH.email_domain),
    FixtureDiscom(EAST.name, "ETD", EAST.email_domain),
]

LOGINS = [
    FixtureLogin("ntd-member", "member", "member@north-discom.example", "NTD", False),
    FixtureLogin("test-admin", "admin", "admin@itped.example", None, False),
    FixtureLogin("test-reviewer", "reviewer", "reviewer@itped.example", None, False),
    FixtureLogin("test-reviewer-alt", "reviewer", "reviewer-alt@itped.example", None, True),
    FixtureLogin("test-approver", "approver", "approver@itped.example", None, False),
]
