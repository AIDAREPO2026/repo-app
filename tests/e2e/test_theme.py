"""P1-UI-02: the theme switcher changes the theme at once and remembers it."""

from playwright.sync_api import Page, expect

from tests.e2e.axe import blocking_violations


def test_p1_ui_02_theme_choice_applies_and_survives_reload(page: Page) -> None:
    page.emulate_media(color_scheme="light")
    page.goto("/login")
    html = page.locator("html")

    page.get_by_role("button", name="Dark").click()
    expect(html).to_have_class("theme-dark")
    assert blocking_violations(page) == []

    page.reload()
    expect(html).to_have_class("theme-dark")
    expect(page.get_by_role("button", name="Dark")).to_have_attribute("aria-pressed", "true")

    page.get_by_role("button", name="System").click()
    expect(html).to_have_class("")
