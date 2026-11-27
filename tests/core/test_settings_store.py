import pytest
from sqlalchemy.orm import Session

from app.audit.service import SYSTEM
from app.core.settings_store import SETTING_RULES, SettingError, get_setting, set_setting


def test_p0_set_02_setting_defaults(db: Session) -> None:
    for key, rule in SETTING_RULES.items():
        assert get_setting(db, key) == rule.default


def test_p0_set_02_set_setting_stores_value(db: Session) -> None:
    set_setting(db, "limit_image_mb", 10, actor=SYSTEM)

    assert get_setting(db, "limit_image_mb") == 10


def test_d01_image_limit_cannot_exceed_20(db: Session) -> None:
    with pytest.raises(SettingError, match="not be above 20"):
        set_setting(db, "limit_image_mb", 21, actor=SYSTEM)

    assert get_setting(db, "limit_image_mb") == 20


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("limit_document_mb", 0),
        ("limit_document_mb", "25"),
        ("limit_document_mb", True),
        ("sixth_session_policy", "allow"),
        ("not_a_setting", 1),
    ],
)
def test_p0_set_02_set_setting_refuses_bad_values(db: Session, key: str, value: int | str) -> None:
    with pytest.raises(SettingError):
        set_setting(db, key, value, actor=SYSTEM)
