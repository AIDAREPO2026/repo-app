"""P1-UI-02 acceptance: the style guide passes axe in light and dark, and reduced motion stops movement.

The style guide is for privileged logins, so these tests sign in with E2E_ADMIN_USER_ID,
E2E_ADMIN_PASSWORD and the authenticator secret E2E_ADMIN_TOTP_SECRET of an Admin enrolled
with an app, and are skipped when those are not set (seeded logins come with P0-QA-02).
"""

import os
from collections.abc import Iterator
from typing import Any

import pyotp
import pytest
from playwright.sync_api import Browser, Page

from tests.e2e.axe import blocking_violations

ADMIN_USER_ID = os.environ.get("E2E_ADMIN_USER_ID", "")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "")
ADMIN_TOTP_SECRET = os.environ.get("E2E_ADMIN_TOTP_SECRET", "")

pytestmark = pytest.mark.skipif(
    not (ADMIN_USER_ID and ADMIN_PASSWORD and ADMIN_TOTP_SECRET),
    reason="Needs E2E_ADMIN_USER_ID, E2E_ADMIN_PASSWORD and E2E_ADMIN_TOTP_SECRET",
)


def password_step(page: Page) -> None:
    """Sign in with the e2e Admin's password, stopping at the code page."""
    page.goto("/login")
    page.get_by_label("User ID").fill(ADMIN_USER_ID)
    page.get_by_label("Password").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url("**/mfa")


@pytest.fixture(scope="session")
def admin_state(browser: Browser, browser_context_args: dict[str, Any]) -> dict[str, Any]:
    """Sign the e2e Admin in once, code included, and return the browser state every test reuses.

    Once, because an authenticator code works only once (FR-2.8): a second sign-in within the
    same 30 seconds would be refused.
    """
    context = browser.new_context(**browser_context_args)
    page = context.new_page()
    password_step(page)
    page.get_by_label("6-digit code").fill(pyotp.TOTP(ADMIN_TOTP_SECRET).now())
    page.get_by_role("button", name="Confirm").click()
    page.wait_for_url("**/dashboard/admin")
    state: dict[str, Any] = context.storage_state()  # type: ignore[assignment]
    context.close()
    return state


@pytest.fixture
def admin_page(
    browser: Browser, browser_context_args: dict[str, Any], admin_state: dict[str, Any]
) -> Iterator[Page]:
    """A new page signed in as the e2e Admin."""
    context = browser.new_context(**browser_context_args, storage_state=admin_state)
    yield context.new_page()
    context.close()


def choose_theme(page: Page, scheme: str) -> None:
    """Save the light or dark choice, as the theme button would."""
    page.add_init_script(f"localStorage.setItem('aida-theme', '{scheme}')")


def open_styleguide(page: Page) -> None:
    """Open the style guide as the e2e Admin."""
    page.goto("/_styleguide")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_p1_ui_02_axe_light_and_dark(admin_page: Page, scheme: str) -> None:
    page = admin_page
    choose_theme(page, scheme)
    open_styleguide(page)

    assert blocking_violations(page) == []


def test_p1_ui_02_reduced_motion(admin_page: Page) -> None:
    page = admin_page
    page.emulate_media(reduced_motion="reduce")
    open_styleguide(page)

    page.get_by_role("button", name="Open drawer").first.click()
    drawer = page.locator("#light-drawer")
    drawer.wait_for(state="visible")

    # The drawer appears in place: no slide, only the short cross-fade.
    assert token(page, "--aida-drawer-offset") == "0%"
    assert drawer.evaluate("element => getComputedStyle(element).transform") in (
        "none",
        "matrix(1, 0, 0, 1, 0, 0)",
    )
    assert token(page, "--aida-press-scale") == "1"


def token(page: Page, name: str) -> str:
    """Return a design token's value as the page resolves it."""
    return page.evaluate(f"getComputedStyle(document.documentElement).getPropertyValue('{name}').trim()")


@pytest.mark.parametrize("path", ["/dashboard/admin", "/admin/accounts", "/admin/discoms"])
@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_p1_ui_02_app_shell_passes_axe(admin_page: Page, scheme: str, path: str) -> None:
    page = admin_page
    choose_theme(page, scheme)
    page.goto(path)

    assert page.get_by_role("navigation", name="Main").is_visible()
    assert blocking_violations(page) == []


def test_p1_ui_02_small_screen_menu_drawer(admin_page: Page) -> None:
    page = admin_page
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto("/dashboard/admin")

    page.get_by_role("button", name="Open menu").click()
    menu = page.get_by_role("navigation", name="Menu")
    menu.wait_for(state="visible")

    assert menu.get_by_role("link", name="Dashboard").get_attribute("aria-current") == "page"
    assert blocking_violations(page) == []
    page.keyboard.press("Escape")
    menu.wait_for(state="hidden")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_p1_acc_10_code_page_passes_axe(page: Page, scheme: str) -> None:
    choose_theme(page, scheme)
    password_step(page)

    assert page.get_by_label("6-digit code").is_visible()
    assert blocking_violations(page) == []
