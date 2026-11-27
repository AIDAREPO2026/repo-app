"""Password hashing with argon2id, and the password policy (FR-1.7, security.md authentication)."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.constants import PASSWORD_MIN_LENGTH

# argon2-cffi's recommended argon2id parameters (RFC 9106). The hasher holds settings only.
HASHER = PasswordHasher()


def hash_password(plain: str) -> str:
    """Return the argon2id hash of a password."""
    return HASHER.hash(plain)


def verify_password(stored_hash: str, plain: str) -> str | None:
    """Return the hash to keep if the password matches, or None if it does not.

    The returned hash is a fresh one when the stored hash used older parameters, so
    the caller saves it and hashes move to the current parameters as people sign in.
    """
    try:
        HASHER.verify(stored_hash, plain)
    except (VerificationError, InvalidHashError):
        return None
    if HASHER.check_needs_rehash(stored_hash):
        return hash_password(plain)
    return stored_hash


def check_password_policy(plain: str, user_id: str) -> list[str]:
    """Return what is wrong with a new password, as messages for the form. Empty means it is allowed."""
    problems = []
    if len(plain) < PASSWORD_MIN_LENGTH:
        problems.append(f"Use at least {PASSWORD_MIN_LENGTH} characters.")
    if not any(character.isalpha() for character in plain):
        problems.append("Include at least one letter.")
    if not any(character.isdigit() for character in plain):
        problems.append("Include at least one number.")
    if not any(_is_symbol(character) for character in plain):
        problems.append("Include at least one symbol, such as ! or #.")
    if user_id and user_id.lower() in plain.lower():
        problems.append("Do not include your User ID.")
    return problems


def _is_symbol(character: str) -> bool:
    """Return True for a character that is not a letter, number or space."""
    return not character.isalnum() and not character.isspace()
