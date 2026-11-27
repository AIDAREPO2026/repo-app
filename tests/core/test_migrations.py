from alembic import command
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

from tests.conftest import alembic_config


def test_p0_set_02_migrations_upgrade_and_downgrade(engine: Engine) -> None:
    config = alembic_config()

    command.downgrade(config, "base")
    assert not {"app_setting", "audit_event"} & set(inspect(engine).get_table_names())

    command.upgrade(config, "head")
    assert {"app_setting", "audit_event"} <= set(inspect(engine).get_table_names())
