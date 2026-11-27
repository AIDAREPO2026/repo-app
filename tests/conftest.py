"""Shared test setup: a real PostgreSQL test database, migrated once per run."""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# A separate database, because the migration test drops every table in it.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://aida:aida@localhost:5434/aida_test"
)

# Safe placeholder values so the app can be created in tests. Set before app imports.
TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": TEST_DATABASE_URL,
    "REDIS_URL": "redis://localhost:6379/15",
    "SECRET_KEY": "test-secret",
    "FERNET_KEY": "test-fernet",
    "IP_HASH_SALT": "test-salt",
}
os.environ.update(TEST_ENV)


def alembic_config() -> AlembicConfig:
    """Return an Alembic config pointed at the test database."""
    config = AlembicConfig("alembic.ini")
    config.attributes["database_url"] = TEST_DATABASE_URL
    return config


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Migrate the test database to head and yield an engine for it."""
    command.upgrade(alembic_config(), "head")
    test_engine = create_engine(TEST_DATABASE_URL)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Yield a session whose changes are rolled back after each test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        yield session
        session.close()
        transaction.rollback()
