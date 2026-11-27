"""Database engine, sessions and the shared declarative base."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Fixed constraint names, so Alembic migrations can drop and rename them reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def one_of(column: str, values: tuple[str, ...]) -> str:
    """Return a CHECK expression limiting a text column to fixed values (data-model.md conventions)."""
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class Base(DeclarativeBase):
    """Base class for every table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def make_session_factory(database_url: str) -> sessionmaker[Session]:
    """Create the engine and a factory for sessions bound to it."""
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(engine, expire_on_commit=False)


def get_db(request: Request) -> Iterator[Session]:
    """Yield a session that commits if the route succeeds and rolls back if it raises."""
    session: Session = request.app.state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# scope="function" commits before the response is sent. FastAPI's default runs the
# commit after the response, so a failed commit would never reach the user.
DbSession = Annotated[Session, Depends(get_db, scope="function")]
