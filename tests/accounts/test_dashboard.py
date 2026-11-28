import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.accounts.models import Organisation
from app.accounts.service import admin_overview
from app.core.constants import LOGIN_TYPES
from app.main import create_app
from tests.accounts.conftest import SignIn
from tests.core.test_design_system import INLINE_SCRIPT


@pytest.fixture(scope="module")
def app() -> FastAPI:
    return create_app()


@pytest.mark.parametrize("login_type", LOGIN_TYPES)
def test_p1_ui_01_dashboard_shell_has_landmarks(app: FastAPI, sign_in: SignIn, login_type: str) -> None:
    sign_in(app, login_type)
    response = TestClient(app).get(f"/dashboard/{login_type}")

    assert response.status_code == 200
    html = response.text
    assert '<a href="#main"' in html  # skip link
    assert '<main id="main"' in html
    assert '<nav aria-label="Main">' in html
    assert f'href="/dashboard/{login_type}"' in html
    assert 'aria-current="page"' in html
    assert INLINE_SCRIPT.findall(html) == []  # no inline scripts, so the CSP can stay strict
    assert "style=" not in html


def test_p1_ui_01_unknown_login_type_is_404(app: FastAPI) -> None:
    assert TestClient(app).get("/dashboard/visitor").status_code == 404


def test_p1_ui_01_stylesheet_is_served(app: FastAPI) -> None:
    response = TestClient(app).get("/static/css/app.css")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/css")


def test_p1_ui_02_admin_overview_counts_only_active_discoms(db: Session) -> None:
    before = admin_overview(db)["active_discoms"]
    suffix = uuid.uuid4().hex[:8]
    db.add(Organisation(name=f"Active {suffix}", email_domain=f"active-{suffix}.in"))
    db.add(Organisation(name=f"Inactive {suffix}", email_domain=f"inactive-{suffix}.in", status="inactive"))
    db.flush()

    assert admin_overview(db)["active_discoms"] == before + 1
