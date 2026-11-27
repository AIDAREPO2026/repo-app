"""Shared test setup: a real PostgreSQL test database, migrated once per run."""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

# A separate database, because the migration test drops every table in it.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://aida:aida@localhost:5434/aida_test"
)

TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6390/15")

# Safe placeholder values so the app can be created in tests. Set before app imports.
TEST_ENV = {
    "APP_ENV": "test",
    "DATABASE_URL": TEST_DATABASE_URL,
    "REDIS_URL": TEST_REDIS_URL,
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


# Servers create the application role; the test database needs it so migrations run their grants.
CREATE_APP_ROLE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aida_app') THEN
        CREATE ROLE aida_app NOLOGIN;
    END IF;
END;
$$;
"""


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Create the app role, migrate the test database to head and yield an engine for it."""
    test_engine = create_engine(TEST_DATABASE_URL)
    with test_engine.begin() as connection:
        connection.execute(text(CREATE_APP_ROLE))
    command.upgrade(alembic_config(), "head")
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
