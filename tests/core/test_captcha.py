"""Spike tests for the CAPTCHA (P0-SEC-01), kept for reuse in P1-ACC-02.

`solve()` does what the browser widget does, so later tests can send a solved CAPTCHA.
"""

import base64
import json
from collections.abc import Iterator
from datetime import timedelta

import altcha
import pytest
from redis import Redis

from app.core import captcha
from app.core.time import utc_now
from tests.conftest import TEST_REDIS_URL

SECRET = "test-captcha-secret"  # noqa: S105 - a test value, not a real secret


@pytest.fixture
def redis_client() -> Iterator[Redis]:
    """A Redis client on the test database, emptied before and after each test."""
    client = Redis.from_url(TEST_REDIS_URL)
    client.flushdb()
    yield client
    client.flushdb()


def solve(challenge: dict[str, object]) -> str:
    """Solve a challenge as the widget would, and return the payload it posts."""
    parsed = altcha.Challenge.from_dict(challenge)
    solution = altcha.solve_challenge(parsed)
    assert solution is not None
    return altcha.Payload(parsed, solution).to_base64()


def test_p0_sec_01_solved_challenge_accepted(redis_client: Redis) -> None:
    payload = solve(captcha.new_challenge(SECRET))

    assert captcha.verify(payload, SECRET, redis_client) is True


def test_p0_sec_01_replayed_challenge_refused(redis_client: Redis) -> None:
    payload = solve(captcha.new_challenge(SECRET))

    assert captcha.verify(payload, SECRET, redis_client) is True
    assert captcha.verify(payload, SECRET, redis_client) is False


def test_p0_sec_01_challenge_signed_by_another_key_refused(redis_client: Redis) -> None:
    payload = solve(captcha.new_challenge("someone-elses-secret"))

    assert captcha.verify(payload, SECRET, redis_client) is False


def test_p0_sec_01_expired_challenge_refused(redis_client: Redis) -> None:
    expired = altcha.create_challenge(
        captcha.ALGORITHM, 1, expires_at=utc_now() - timedelta(minutes=1), hmac_secret=SECRET
    )
    payload = solve(expired.to_dict())

    assert captcha.verify(payload, SECRET, redis_client) is False


def test_p0_sec_01_wrong_answer_refused(redis_client: Redis) -> None:
    payload = solve(captcha.new_challenge(SECRET))
    data = json.loads(base64.b64decode(payload))
    data["solution"]["counter"] += 1
    tampered = base64.b64encode(json.dumps(data).encode()).decode()

    assert captcha.verify(tampered, SECRET, redis_client) is False


@pytest.mark.parametrize("payload", ["", "not-base64!", "x" * 5_000])
def test_p0_sec_01_malformed_payload_refused(redis_client: Redis, payload: str) -> None:
    assert captcha.verify(payload, SECRET, redis_client) is False
