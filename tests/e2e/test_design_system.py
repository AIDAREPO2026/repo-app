"""P1-UI-02 acceptance: the style guide passes axe in light and dark, and reduced motion stops movement.

The style guide is for privileged logins, so these tests sign in with E2E_ADMIN_USER_ID and
E2E_ADMIN_PASSWORD, and are skipped when those are not set (seeded logins come with P0-QA-02).
"""

import os

import pytest
from playwright.sync_api import Page

from tests.e2e.axe import blocking_violations

ADMIN_USER_ID = os.environ.get("E2E_ADMIN_USER_ID", "")
ADMIN_PASSWORD = os.environ.get("E2E_ADMIN_PASSWORD", "")

pytestmark = pytest.mark.skipif(
    not (ADMIN_USER_ID and ADMIN_PASSWORD), reason="Needs E2E_ADMIN_USER_ID and E2E_ADMIN_PASSWORD"
)


def sign_in_to(page: Page, path: str) -> None:
    """Sign in as the e2e Admin and open a page."""
    page.goto(f"/login?next={path}")
    page.get_by_label("User ID").fill(ADMIN_USER_ID)
    page.get_by_label("Password").fill(ADMIN_PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    page.wait_for_url(f"**{path}")


def open_styleguide(page: Page) -> None:
    """Sign in as the e2e Admin and open the style guide."""
    sign_in_to(page, "/_styleguide")


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_p1_ui_02_axe_light_and_dark(page: Page, scheme: str) -> None:
    page.emulate_media(color_scheme=scheme)
    open_styleguide(page)

    assert blocking_violations(page) == []


def test_p1_ui_02_reduced_motion(page: Page) -> None:
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


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_p1_ui_02_app_shell_passes_axe(page: Page, scheme: str) -> None:
    page.emulate_media(color_scheme=scheme)
    sign_in_to(page, "/dashboard/admin")

    assert page.get_by_role("navigation", name="Main").is_visible()
    assert blocking_violations(page) == []


def test_p1_ui_02_small_screen_menu_drawer(page: Page) -> None:
    page.set_viewport_size({"width": 375, "height": 812})
    sign_in_to(page, "/dashboard/admin")

    page.get_by_role("button", name="Open menu").click()
    menu = page.get_by_role("navigation", name="Menu")
    menu.wait_for(state="visible")

    assert menu.get_by_role("link", name="Dashboard").get_attribute("aria-current") == "page"
    assert blocking_violations(page) == []
    page.keyboard.press("Escape")
    menu.wait_for(state="hidden")
