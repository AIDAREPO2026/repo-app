"""P1-UI-02: one click changes the theme, and the choice is remembered."""

from playwright.sync_api import Page, expect

from tests.e2e.axe import blocking_violations


def test_p1_ui_02_light_is_the_default_on_a_dark_device(page: Page) -> None:
    page.emulate_media(color_scheme="dark")
    page.goto("/login")

    expect(page.locator("html")).to_have_class("theme-light")
    expect(page.get_by_role("button", name="Switch to dark theme")).to_be_visible()


def test_p1_ui_02_one_click_switches_the_theme_and_survives_reload(page: Page) -> None:
    page.goto("/login")
    html = page.locator("html")

    page.get_by_role("button", name="Switch to dark theme").click()
    expect(html).to_have_class("theme-dark")
    assert blocking_violations(page) == []

    page.reload()
    expect(html).to_have_class("theme-dark")

    page.get_by_role("button", name="Switch to light theme").click()
    expect(html).to_have_class("theme-light")
