"""End-to-end tests with Playwright. They run only when E2E_BASE_URL names a running portal:

    E2E_BASE_URL=https://localhost:8443 uv run pytest tests/e2e

Without it, `pytest` skips this folder, so the normal test run needs no browser or server.
"""

import os
from typing import Any
from urllib.parse import urlsplit

import pytest

E2E_BASE_URL = os.environ.get("E2E_BASE_URL", "").rstrip("/")

# The local Docker stack uses a self-signed certificate. Staging and live always check it.
LOCAL_HOSTS = {"localhost", "127.0.0.1"}

if not E2E_BASE_URL:
    collect_ignore_glob = ["test_*.py"]


@pytest.fixture(scope="session")
def base_url() -> str:
    """The portal under test; page.goto() paths are relative to it."""
    return E2E_BASE_URL


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict[str, Any], base_url: str) -> dict[str, Any]:
    """Accept the self-signed certificate on local hosts only."""
    if urlsplit(base_url).hostname in LOCAL_HOSTS:
        return {**browser_context_args, "ignore_https_errors": True}
    return browser_context_args
