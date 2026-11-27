import logging

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.main import create_app

SECRET = "internal-detail-7f3a"  # noqa: S105 - a marker string, not a password


@pytest.fixture
def app_with_failing_routes() -> FastAPI:
    """The real app plus two routes that fail on purpose."""
    application = create_app()

    @application.get("/boom")
    def boom() -> None:
        raise RuntimeError(SECRET)

    @application.get("/forbidden")
    def forbidden() -> None:
        raise HTTPException(status_code=403, detail=SECRET)

    return application


def test_p1_ui_01_error_pages_hide_details(
    app_with_failing_routes: FastAPI, caplog: pytest.LogCaptureFixture
) -> None:
    client = TestClient(app_with_failing_routes, raise_server_exceptions=False)
    # create_app() replaced the root handlers, so listen on the error module's logger directly.
    logging.getLogger("app.core.errors").addHandler(caplog.handler)
    try:
        response = client.get("/boom")
    finally:
        logging.getLogger("app.core.errors").removeHandler(caplog.handler)

    assert response.status_code == 500
    assert "Something went wrong" in response.text
    assert SECRET not in response.text
    assert "Traceback" not in response.text
    # The trace goes to the server log instead.
    assert any(record.exc_info and SECRET in str(record.exc_info[1]) for record in caplog.records)


def test_p1_ui_01_forbidden_page_hides_detail(app_with_failing_routes: FastAPI) -> None:
    response = TestClient(app_with_failing_routes).get("/forbidden")

    assert response.status_code == 403
    assert "Access denied" in response.text
    assert SECRET not in response.text


def test_p1_ui_01_unknown_page_shows_friendly_404() -> None:
    response = TestClient(create_app()).get("/no-such-page")

    assert response.status_code == 404
    assert "Page not found" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_p1_ui_01_debug_mode_is_off() -> None:
    # In debug mode Starlette would send the stack trace instead of the 500 page.
    assert create_app().debug is False
