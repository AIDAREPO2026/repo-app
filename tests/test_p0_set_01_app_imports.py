"""P0-SET-01: the skeleton imports cleanly and the app starts."""

import importlib

from fastapi.testclient import TestClient

MODULES = ["accounts", "audit", "content", "workflow", "search", "experts", "gallery", "kpi", "public"]
LAYERS = ["router", "service", "models", "schemas"]


def test_p0_set_01_app_imports() -> None:
    """Every module has the four layer files, each with a docstring."""
    for module in MODULES:
        for layer in LAYERS:
            imported = importlib.import_module(f"app.{module}.{layer}")
            assert imported.__doc__, f"app/{module}/{layer}.py needs a docstring"


def test_p0_set_01_healthz() -> None:
    """The app starts and answers its health check."""
    from app.main import app

    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
