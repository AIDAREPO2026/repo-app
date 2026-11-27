"""Run Alembic migrations against the database named in the app config."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

# Every models module is imported so autogenerate sees all tables. Add new ones here.
import app.accounts.models
import app.audit.models
import app.content.models
import app.core.settings_store
import app.experts.models
import app.gallery.models
import app.kpi.models
import app.public.models
import app.search.models
import app.workflow.models
from app.core.config import load_config
from app.core.db import Base

if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def database_url() -> str:
    """Use a URL passed by the caller (tests), otherwise the app's own config."""
    passed = context.config.attributes.get("database_url")
    if passed:
        return str(passed)
    return load_config().database_url


def run_migrations() -> None:
    """Apply migrations inside one transaction per run."""
    engine = create_engine(database_url())
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations()
