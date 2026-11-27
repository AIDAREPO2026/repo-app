from datetime import UTC, datetime

import pytest

from app.core.time import to_ist, utc_now


def test_p0_set_02_utc_now_is_aware_utc() -> None:
    assert utc_now().utcoffset() is not None
    assert utc_now().utcoffset().total_seconds() == 0  # type: ignore[union-attr]


def test_p0_set_02_to_ist_adds_five_and_a_half_hours() -> None:
    assert to_ist(datetime(2026, 11, 27, 0, 0, tzinfo=UTC)).strftime("%H:%M %Z") == "05:30 IST"


def test_p0_set_02_to_ist_refuses_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        to_ist(datetime(2026, 11, 27))
