"""Second-factor helpers: authenticator app secrets, their codes and the enrolment QR code (FR-2.8).

The business rules that use them (who needs MFA, enrolment, resets) live in service.py.
"""

import base64
import hmac
import io

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet

from app.core.config import load_config
from app.core.time import utc_now

ISSUER = "AIDA portal"


def new_totp_secret() -> str:
    """Return a new random authenticator secret, in the base32 form apps expect."""
    return pyotp.random_base32()


def encrypt_secret(secret: str) -> str:
    """Encrypt an authenticator secret with the Fernet key from the environment, for storing."""
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_secret(stored: str) -> str:
    """Decrypt a stored authenticator secret."""
    return _fernet().decrypt(stored.encode()).decode()


def matching_totp_step(secret: str, code: str, last_step: int | None) -> int | None:
    """Return the time step a code belongs to, or None if it is wrong or already used.

    One step either side of now is accepted, for clock drift on the phone. A step at or
    before the last one accepted is refused, so a code cannot be used twice.
    """
    totp = pyotp.TOTP(secret)
    current = totp.timecode(utc_now())
    for step in (current - 1, current, current + 1):
        if last_step is not None and step <= last_step:
            continue
        if hmac.compare_digest(totp.generate_otp(step), code):
            return step
    return None


def provisioning_uri(secret: str, user_id: str) -> str:
    """Return the otpauth:// address an authenticator app reads from the QR code."""
    return pyotp.TOTP(secret).provisioning_uri(name=user_id, issuer_name=ISSUER)


def qr_code_data_uri(text: str) -> str:
    """Return an SVG QR code for some text as a data: URI, which the page CSP allows for images."""
    image = qrcode.make(text, image_factory=qrcode.image.svg.SvgPathImage, border=2)
    buffer = io.BytesIO()
    image.save(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/svg+xml;base64,{encoded}"


def _fernet() -> Fernet:
    """Return the Fernet cipher for the key in FERNET_KEY."""
    return Fernet(load_config().fernet_key.encode())
