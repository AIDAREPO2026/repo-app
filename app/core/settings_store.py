"""Admin-editable settings: the app_setting table, their rules, and get/set functions."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.audit.service import Actor, record
from app.core.constants import IMAGE_LIMIT_MAX_MB
from app.core.db import Base
from app.core.time import utc_now

SettingValue = int | str


class AppSetting(Base):
    """A stored setting value. A key with no row uses its default."""

    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[SettingValue] = mapped_column(JSONB)
    # Becomes a foreign key to login once that table exists (P1-ACC-08).
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


@dataclass(frozen=True)
class SettingRule:
    """The default and allowed values of one setting."""

    default: SettingValue
    minimum: int | None = None
    maximum: int | None = None
    choices: tuple[str, ...] = field(default_factory=tuple)


# The settings table in docs/architecture.md. Change both together.
SETTING_RULES: dict[str, SettingRule] = {
    "limit_document_mb": SettingRule(default=25, minimum=1),  # FR-3.5
    "limit_image_mb": SettingRule(default=20, minimum=1, maximum=IMAGE_LIMIT_MAX_MB),  # FR-3.5, D-01
    "limit_media_mb": SettingRule(default=1024, minimum=1),  # FR-3.5
    "sixth_session_policy": SettingRule(default="block", choices=("block", "end_oldest")),  # FR-2.3, D-10
    "anon_downloads_per_hour": SettingRule(default=50, minimum=1),  # FR-13.7
    "newly_added_count": SettingRule(default=2, minimum=1),  # FR-6.1, Q-05
    "newly_added_days": SettingRule(default=15, minimum=1),  # FR-6.1
    # D-14: share of the data disk kept free. Uploads are refused when they would eat into it.
    "storage_reserve_percent": SettingRule(default=10, minimum=5, maximum=50),
    "digest_frequency": SettingRule(default="daily", choices=("daily", "weekly")),  # FR-6.5
}


class SettingError(ValueError):
    """Raised when a key is unknown or a value breaks its setting's rule."""


def get_setting(db: Session, key: str) -> SettingValue:
    """Return the stored value of a setting, or its default when none is stored."""
    rule = _rule_for(key)
    stored = db.get(AppSetting, key)
    if stored is None:
        return rule.default
    return stored.value


def set_setting(db: Session, key: str, value: SettingValue, actor: Actor) -> None:
    """Validate and store a setting value, and audit the change with its old and new values."""
    _validate(key, value)
    old_value = get_setting(db, key)
    stored = db.get(AppSetting, key)
    if stored is None:
        stored = AppSetting(key=key)
        db.add(stored)
    stored.value = value
    stored.updated_by = actor.login_id
    stored.updated_at = utc_now()
    db.flush()
    record(db, actor, "settings.update", "setting", key, "success", {"old": old_value, "new": value})


def _rule_for(key: str) -> SettingRule:
    """Return the rule for a key, refusing keys that are not settings."""
    rule = SETTING_RULES.get(key)
    if rule is None:
        raise SettingError(f"Unknown setting {key!r}")
    return rule


def _validate(key: str, value: SettingValue) -> None:
    """Refuse a value of the wrong type or outside the setting's bounds."""
    rule = _rule_for(key)
    if rule.choices:
        if value not in rule.choices:
            raise SettingError(f"{key} must be one of {', '.join(rule.choices)}")
        return
    # bool is a subclass of int, so it must be refused explicitly.
    if not isinstance(value, int) or isinstance(value, bool):
        raise SettingError(f"{key} must be a whole number")
    if rule.minimum is not None and value < rule.minimum:
        raise SettingError(f"{key} must be at least {rule.minimum}")
    if rule.maximum is not None and value > rule.maximum:
        raise SettingError(f"{key} must not be above {rule.maximum}")
