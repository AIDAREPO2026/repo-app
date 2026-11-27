"""Check that the app's dependencies answer, for /healthz."""

import logging

from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)


def database_answers(session_factory: sessionmaker[Session]) -> bool:
    """Return True if the database answers a trivial query."""
    try:
        with session_factory() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        logger.warning("Health check: the database did not answer", exc_info=True)
        return False
    return True


def redis_answers(client: Redis) -> bool:
    """Return True if Redis answers a ping."""
    try:
        client.ping()
    except Exception:
        logger.warning("Health check: Redis did not answer", exc_info=True)
        return False
    return True
