"""P1-UI-01 acceptance: the layout passes axe and works by keyboard alone."""

import pytest
from playwright.sync_api import Page, expect

from app.core.constants import LOGIN_TYPES
from tests.e2e.axe import blocking_violations


@pytest.mark.parametrize("login_type", LOGIN_TYPES)
def test_p1_ui_01_dashboard_passes_axe(page: Page, login_type: str) -> None:
    page.goto(f"/dashboard/{login_type}")

    assert blocking_violations(page) == []


def test_p1_ui_01_error_page_passes_axe(page: Page) -> None:
    page.goto("/no-such-page")

    assert blocking_violations(page) == []


def test_p1_ui_01_skip_link_is_first_and_visible(page: Page) -> None:
    page.goto("/dashboard/member")
    page.keyboard.press("Tab")

    skip_link = page.get_by_role("link", name="Skip to main content")
    expect(skip_link).to_be_focused()
    expect(skip_link).to_be_visible()

    page.keyboard.press("Enter")
    expect(page.locator("main")).to_be_focused()


def test_p1_ui_01_focus_indicator_is_visible(page: Page) -> None:
    page.goto("/dashboard/member")
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")
    page.keyboard.press("Tab")

    menu_link = page.get_by_role("link", name="Dashboard")
    expect(menu_link).to_be_focused()
    outline = menu_link.evaluate("element => getComputedStyle(element).outlineStyle")
    assert outline != "none"
