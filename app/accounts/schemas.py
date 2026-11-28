"""Accounts: schemas layer.

Pydantic input and view schemas. Views for Members and visitors must never contain admin-only fields.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SignInForm(BaseModel):
    """The sign-in form. Limits stop oversized input before any password is hashed."""

    user_id: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)
    # Where to go after signing in. Checked by after_sign_in_path, never followed as given.
    next: str = Field(default="", max_length=2000)


# A plain shape check. Delivery of the set-password email is the real test of an address.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
USER_ID_PATTERN = r"^[a-z0-9._-]{4,50}$"


class PersonForm(BaseModel):
    """The named person behind a privileged account (FR-2.7)."""

    full_name: str = Field(min_length=1, max_length=200)
    email: str = Field(max_length=254, pattern=EMAIL_PATTERN)
    user_id: str = Field(pattern=USER_ID_PATTERN)


class PrivilegedAccountForm(PersonForm):
    """A new Admin, Reviewer or Approver account."""

    login_type: Literal["admin", "reviewer", "approver"]
    # Reviewers only: the alternate covers when the primary Reviewer cannot.
    is_alternate: bool = False


class ReviewerRoleForm(BaseModel):
    """Make a Reviewer the primary or the alternate."""

    is_alternate: bool


class SetPasswordForm(BaseModel):
    """The set-password form reached from an emailed link."""

    password: str = Field(min_length=1, max_length=1024)
    confirm_password: str = Field(min_length=1, max_length=1024)


class MfaSetupForm(BaseModel):
    """The second-factor method chosen at enrolment (FR-2.8)."""

    method: Literal["totp", "email"]
    next: str = Field(default="", max_length=2000)


class MfaCodeForm(BaseModel):
    """A code from an authenticator app or an email. Any wrong shape is simply a wrong code."""

    code: str = Field(min_length=1, max_length=12)
    # Only used at enrolment; an enrolled login's own method always wins.
    method: Literal["totp", "email"] = "totp"
    next: str = Field(default="", max_length=2000)


class MfaOffForm(BaseModel):
    """A current code, asked for before a Member turns two-step sign-in off."""

    code: str = Field(min_length=1, max_length=12)


class NextForm(BaseModel):
    """A form whose only field is where to go afterwards."""

    next: str = Field(default="", max_length=2000)


# A host name such as tpddl.co.in: labels of letters, digits and inner hyphens, then a TLD.
DOMAIN_PATTERN = r"^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"


class DiscomForm(BaseModel):
    """A recognised Discom and the email domain its staff use (FR-1.6, D-11)."""

    name: str = Field(min_length=1, max_length=200)
    email_domain: str = Field(max_length=253, pattern=DOMAIN_PATTERN)

    @field_validator("name", mode="before")
    @classmethod
    def tidy_name(cls, value: object) -> object:
        """Drop spaces around the name, so " BSES " and "BSES" are the same Discom."""
        return value.strip() if isinstance(value, str) else value

    @field_validator("email_domain", mode="before")
    @classmethod
    def tidy_domain(cls, value: object) -> object:
        """Store domains lowercase, without spaces or a leading @, as people often type them."""
        if not isinstance(value, str):
            return value
        return value.strip().lower().removeprefix("@")


class DiscomImportForm(BaseModel):
    """The CSV text carried from the import preview to the save step."""

    csv_text: str = Field(min_length=1, max_length=100_000)
