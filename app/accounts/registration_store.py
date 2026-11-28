"""What a registration in progress remembers, kept in Redis and thrown away by expiry (P1-ACC-02).

Nothing here is a login yet, so none of it goes in the database. Only SHA-256 hashes of the
visitor's token and of the emailed code are stored.
"""

import hmac
import json
from typing import cast

from redis import Redis

from app.core.constants import (
    EMAIL_CODE_MAX_TRIES,
    EMAIL_CODE_MINUTES,
    EMAIL_CODE_RESEND_SECONDS,
    REGISTRATION_VERIFIED_MINUTES,
    USER_ID_CHECKS,
)
from app.core.sessions import hash_token, new_token


def _key(kind: str, value: str) -> str:
    return f"registration:{kind}:{hash_token(value).hex()}"


def remember_request(redis: Redis, organisation_id: str, email: str) -> str:
    """Store who asked for a code and return the token that goes in their cookie."""
    token = new_token()
    body = json.dumps({"organisation_id": organisation_id, "email": email})
    redis.set(_key("pending", token), body, ex=EMAIL_CODE_MINUTES * 60)
    return token


def _read(redis: Redis, kind: str, token: str) -> dict[str, str] | None:
    body = cast("bytes | None", redis.get(_key(kind, token)))
    return json.loads(body) if body else None


def may_send_code(redis: Redis, email: str) -> bool:
    """Return True at most once a minute for an address, so nobody's inbox can be flooded."""
    return bool(redis.set(_key("sent", email), "1", nx=True, ex=EMAIL_CODE_RESEND_SECONDS))


def _code_owner(request: dict[str, str]) -> str:
    return f"{request['organisation_id']}|{request['email']}"


def save_code(redis: Redis, organisation_id: str, email: str, code: str) -> None:
    """Keep the code just sent to this address, replacing any earlier one."""
    owner = _code_owner({"organisation_id": organisation_id, "email": email})
    key = _key("code", owner)
    redis.delete(key)
    redis.hset(key, mapping={"hash": hash_token(f"{owner}|{code}").hex(), "tries": 0})
    redis.expire(key, EMAIL_CODE_MINUTES * 60)


def use_code(redis: Redis, token: str, code: str) -> str | None:
    """Return a new token for a verified visitor if the code is right, else None.

    A request that was never sent a code fails the same way as a wrong code. The 5th wrong
    try throws the code away.
    """
    request = _read(redis, "pending", token)
    if request is None:
        return None
    owner = _code_owner(request)
    key = _key("code", owner)
    stored = cast("bytes | None", redis.hget(key, "hash"))
    if stored is None:
        return None
    if not hmac.compare_digest(stored.decode(), hash_token(f"{owner}|{code}").hex()):
        if redis.hincrby(key, "tries", 1) >= EMAIL_CODE_MAX_TRIES:
            redis.delete(key)
        return None
    redis.delete(key, _key("pending", token))
    verified = new_token()
    redis.set(_key("verified", verified), json.dumps(request), ex=REGISTRATION_VERIFIED_MINUTES * 60)
    return verified


def verified_request(redis: Redis, token: str) -> dict[str, str] | None:
    """Return the Discom and email a verified visitor proved, or None."""
    return _read(redis, "verified", token)


def count_user_id_check(redis: Redis, token: str) -> bool:
    """Return False once a verified visitor has asked about too many User IDs."""
    key = _key("checks", token)
    used = redis.incr(key)
    redis.expire(key, REGISTRATION_VERIFIED_MINUTES * 60)
    return used <= USER_ID_CHECKS


def forget_verified(redis: Redis, token: str) -> None:
    """End a verification once its request has been sent."""
    redis.delete(_key("verified", token), _key("checks", token))
