import pytest

from app.core.config import MissingConfigError, load_config


def test_p0_set_02_missing_env_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")
    monkeypatch.delenv("SECRET_KEY")

    with pytest.raises(MissingConfigError, match="DATABASE_URL, SECRET_KEY"):
        load_config(env_file=None)


def test_p0_set_02_config_reads_environment() -> None:
    assert load_config(env_file=None).app_env == "test"


def test_p1_acc_10_invalid_fernet_key_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FERNET_KEY", "change-me")

    with pytest.raises(MissingConfigError, match="FERNET_KEY"):
        load_config(env_file=None)
