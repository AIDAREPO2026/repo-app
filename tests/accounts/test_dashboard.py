import pytest
from fastapi.testclient import TestClient

from app.core.constants import LOGIN_TYPES
from app.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(create_app())


@pytest.mark.parametrize("login_type", LOGIN_TYPES)
def test_p1_ui_01_dashboard_shell_has_landmarks(client: TestClient, login_type: str) -> None:
    response = client.get(f"/dashboard/{login_type}")

    assert response.status_code == 200
    html = response.text
    assert '<a href="#main"' in html  # skip link
    assert '<main id="main"' in html
    assert '<nav aria-label="Main">' in html
    assert f'href="/dashboard/{login_type}"' in html
    assert 'aria-current="page"' in html
    assert "<script" not in html  # no inline scripts, so the CSP can stay strict
    assert "style=" not in html


def test_p1_ui_01_unknown_login_type_is_404(client: TestClient) -> None:
    assert client.get("/dashboard/visitor").status_code == 404


def test_p1_ui_01_stylesheet_is_served(client: TestClient) -> None:
    response = client.get("/static/css/app.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")
