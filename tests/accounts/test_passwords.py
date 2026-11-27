import pytest
from argon2 import PasswordHasher

from app.accounts.passwords import check_password_policy, hash_password, verify_password

GOOD_PASSWORD = "Grid-Meter-2026"  # noqa: S105 - a test value, not a real password


def test_fr_1_7_password_minimum_length() -> None:
    assert check_password_policy("Grid-Mete-1", "discom.one") == ["Use at least 12 characters."]
    assert check_password_policy("Grid-Meter-1", "discom.one") == []


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("123456789012!", "Include at least one letter."),
        ("GridMeterPass!", "Include at least one number."),
        ("GridMeter2026x", "Include at least one symbol, such as ! or #."),
        ("Grid Meter 2026", "Include at least one symbol, such as ! or #."),
    ],
)
def test_fr_1_7_password_character_mix(password: str, problem: str) -> None:
    assert check_password_policy(password, "discom.one") == [problem]


def test_fr_1_7_password_must_not_contain_user_id() -> None:
    assert check_password_policy("My-DISCOM.ONE-2026", "discom.one") == ["Do not include your User ID."]


def test_fr_1_7_password_is_hashed_with_argon2id() -> None:
    stored = hash_password(GOOD_PASSWORD)

    assert stored.startswith("$argon2id$")
    assert GOOD_PASSWORD not in stored
    assert verify_password(stored, GOOD_PASSWORD) == stored
    assert verify_password(stored, "Wrong-Meter-2026") is None
    assert verify_password("not a hash", GOOD_PASSWORD) is None


def test_fr_1_7_old_parameters_are_rehashed() -> None:
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(GOOD_PASSWORD)

    kept = verify_password(weak, GOOD_PASSWORD)

    assert kept is not None and kept != weak
    assert verify_password(kept, GOOD_PASSWORD) == kept
