"""P1-UI-02: the style guide is for privileged logins only, and is not advertised to anyone else."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.accounts.conftest import SignIn

APP = create_app()


def test_p1_ui_02_styleguide_privileged_only_visitor_gets_404() -> None:
    assert TestClient(APP).get("/_styleguide").status_code == 404


@pytest.mark.parametrize(
    ("login_type", "status"), [("member", 404), ("admin", 200), ("reviewer", 200), ("approver", 200)]
)
def test_p1_ui_02_styleguide_privileged_only(sign_in: SignIn, login_type: str, status: int) -> None:
    sign_in(APP, login_type)

    response = TestClient(APP).get("/_styleguide")

    assert response.status_code == status
