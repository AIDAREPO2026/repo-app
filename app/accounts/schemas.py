"""Accounts: schemas layer.

Pydantic input and view schemas. Views for Members and visitors must never contain admin-only fields.
"""

from pydantic import BaseModel, Field


class SignInForm(BaseModel):
    """The sign-in form. Limits stop oversized input before any password is hashed."""

    user_id: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=1024)
    # Where to go after signing in. Checked by after_sign_in_path, never followed as given.
    next: str = Field(default="", max_length=2000)
