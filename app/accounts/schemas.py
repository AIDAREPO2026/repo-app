"""Accounts: schemas layer.

Pydantic input and view schemas. Views for Members and visitors must never contain admin-only fields.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.captcha import MAX_PAYLOAD_LENGTH


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

    @model_validator(mode="before")
    @classmethod
    def alternate_reviewer_is_a_reviewer(cls, data: Any) -> Any:
        """Read the form's single "Alternate Reviewer" choice as a Reviewer who is the alternate."""
        if isinstance(data, dict) and data.get("login_type") == "alternate_reviewer":
            return data | {"login_type": "reviewer", "is_alternate": True}
        return data


class ReviewerRoleForm(BaseModel):
    """Make a Reviewer the primary or the alternate."""

    is_alternate: bool


class ReservedWordForm(BaseModel):
    """A word to reserve, or to free again, and where it applies."""

    word: str = Field(min_length=1, max_length=60)
    where: Literal["anywhere", "parts"]
    # Why it is reserved. Not needed to remove a word.
    category: str = Field(default="other", max_length=30)


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


class DiscomAddForm(DiscomForm):
    """The Add Discom form: a Discom, and the Admin's word that its details were checked."""

    # Not required here, so an unticked box gets a message on the page instead of a bare 422.
    checked: bool = False


class DiscomImportForm(BaseModel):
    """The CSV text carried from the import preview to the save step."""

    csv_text: str = Field(min_length=1, max_length=100_000)


class RegistrationStartForm(BaseModel):
    """Step 1 of registration: which Discom, and an address on its domain (FR-1.1, D-11).

    Only lengths are checked here. The formats are checked by the service after the CAPTCHA,
    so the page can show each problem next to its field instead of a bare 422.
    """

    organisation_id: str = Field(default="", max_length=36)
    email: str = Field(default="", max_length=254)
    # The ALTCHA widget's answer (app.core.captcha). Empty when the widget did not run.
    altcha: str = Field(default="", max_length=MAX_PAYLOAD_LENGTH)

    @field_validator("email", "organisation_id", mode="before")
    @classmethod
    def tidy_text(cls, value: object) -> object:
        """Drop spaces and use lowercase, as email domains are stored."""
        return value.strip().lower() if isinstance(value, str) else value


class RegistrationCodeForm(BaseModel):
    """Step 2: the code from the email."""

    code: str = Field(default="", max_length=20)

    @field_validator("code", mode="before")
    @classmethod
    def drop_spaces(cls, value: object) -> object:
        """People often copy a code with spaces."""
        return value.replace(" ", "") if isinstance(value, str) else value


class RegistrationForm(BaseModel):
    """Step 3: the login a verified visitor asks for (FR-1.1)."""

    user_id: str = Field(default="", max_length=254)
    password: str = Field(default="", max_length=1024)
    confirm_password: str = Field(default="", max_length=1024)

    @field_validator("user_id", mode="before")
    @classmethod
    def tidy_user_id(cls, value: object) -> object:
        """Drop spaces and use lowercase, as User IDs are stored."""
        return value.strip().lower() if isinstance(value, str) else value
