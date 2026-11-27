"""Self-hosted proof-of-work CAPTCHA using ALTCHA (decision record 0006).

The browser widget solves a small puzzle in the background, so there is no image to read
and nothing leaves our servers (FR-1.2, SRS 5.3). The server signs each challenge, checks
the answer and remembers used challenges in Redis, so an answer works only once.
"""

from datetime import timedelta

import altcha
from redis import Redis

from app.core.time import utc_now

ALGORITHM = "PBKDF2/SHA-256"
# About a second of work in a browser: on average 256 tries to hit the "00" key prefix,
# each this many PBKDF2 rounds. Raise it if bots get through; checking one answer stays cheap.
COST = 5_000
EXPIRY = timedelta(minutes=10)
# A real payload is well under 1 KB; anything far larger is refused before parsing.
MAX_PAYLOAD_LENGTH = 4_096
USED_KEY = "captcha:used:{nonce}"


def new_challenge(secret: str) -> dict[str, object]:
    """Return a signed challenge for the widget, ready to send as JSON."""
    challenge = altcha.create_challenge(ALGORITHM, COST, expires_at=utc_now() + EXPIRY, hmac_secret=secret)
    return challenge.to_dict()


def verify(payload: str, secret: str, redis: Redis) -> bool:
    """Return True the first time a correctly solved, unexpired challenge is sent, else False."""
    if not payload or len(payload) > MAX_PAYLOAD_LENGTH:
        return False
    result = altcha.verify_solution(payload, secret)
    if not result.verified:
        return False
    nonce = altcha.Payload.from_base64(payload).challenge.parameters.nonce
    # SET NX succeeds only for the first use, so a replayed answer is refused. The record
    # lives as long as the challenge could still be valid.
    first_use = redis.set(USED_KEY.format(nonce=nonce), "1", nx=True, ex=int(EXPIRY.total_seconds()))
    return bool(first_use)
