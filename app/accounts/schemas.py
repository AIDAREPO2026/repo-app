"""Accounts: schemas layer.

Pydantic input and view schemas. Views for Members and visitors must never contain admin-only fields.
"""

from typing import Literal

from pydantic import BaseModel, Field


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
