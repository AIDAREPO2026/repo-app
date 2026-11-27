from fastapi import FastAPI
from fastapi.testclient import TestClient
from redis import Redis
from sqlalchemy.engine import Engine

from app.core.db import make_session_factory
from app.main import create_app

# Nothing listens on port 1, so connections there fail at once.
UNREACHABLE_REDIS = "redis://localhost:1/0"
UNREACHABLE_DATABASE = "postgresql+psycopg://aida:aida@localhost:1/aida_test?connect_timeout=2"


def healthz(app: FastAPI) -> tuple[int, object]:
    response = TestClient(app).get("/healthz")
    return response.status_code, response.json()


def test_p0_ops_02_healthz_checks_dependencies(engine: Engine) -> None:
    app = create_app()
    assert healthz(app) == (200, {"status": "ok"})

    app.state.redis = Redis.from_url(UNREACHABLE_REDIS, socket_connect_timeout=1)
    assert healthz(app) == (503, {"status": "fail"})


def test_p0_ops_02_healthz_fails_without_database(engine: Engine) -> None:
    app = create_app()
    app.state.session_factory = make_session_factory(UNREACHABLE_DATABASE)

    assert healthz(app) == (503, {"status": "fail"})
