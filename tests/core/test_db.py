from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.audit.service import SYSTEM
from app.core.db import DbSession
from app.core.settings_store import AppSetting, get_setting, set_setting
from app.main import create_app


@pytest.fixture
def app(engine: Engine) -> Iterator[FastAPI]:
    """An app with two routes that change a setting, one of which then fails."""
    application = create_app()

    @application.post("/ok")
    def change_and_succeed(db: DbSession) -> None:
        set_setting(db, "newly_added_days", 30, actor=SYSTEM)

    @application.post("/fail")
    def change_and_fail(db: DbSession) -> None:
        set_setting(db, "newly_added_days", 30, actor=SYSTEM)
        raise RuntimeError("route failed after writing")

    yield application
    # These routes commit for real, so remove what they stored.
    with Session(engine) as session:
        session.execute(delete(AppSetting))
        session.commit()


def stored_days(engine: Engine) -> int | str:
    with Session(engine) as session:
        return get_setting(session, "newly_added_days")


def test_p0_set_02_get_db_commits_on_success(app: FastAPI, engine: Engine) -> None:
    assert TestClient(app).post("/ok").status_code == 200
    assert stored_days(engine) == 30


def test_p0_set_02_get_db_rolls_back_on_error(app: FastAPI, engine: Engine) -> None:
    response = TestClient(app, raise_server_exceptions=False).post("/fail")

    assert response.status_code == 500
    assert stored_days(engine) == 15
