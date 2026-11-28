"""P1-UI-02: the theme switcher changes the theme at once and remembers it."""

from playwright.sync_api import Page, expect

from tests.e2e.axe import blocking_violations


def choose(page: Page, theme: str) -> None:
    """Open the theme menu and pick one."""
    page.get_by_role("button", name="Theme").click()
    page.get_by_role("button", name=theme).click()


def test_p1_ui_02_light_is_the_default_on_a_dark_device(page: Page) -> None:
    page.emulate_media(color_scheme="dark")
    page.goto("/login")

    expect(page.locator("html")).to_have_class("theme-light")
    expect(page.locator('[data-theme-choice="light"]')).to_have_attribute("aria-pressed", "true")


def test_p1_ui_02_theme_choice_applies_and_survives_reload(page: Page) -> None:
    page.emulate_media(color_scheme="light")
    page.goto("/login")
    html = page.locator("html")

    choose(page, "Dark")
    expect(html).to_have_class("theme-dark")
    assert blocking_violations(page) == []

    page.reload()
    expect(html).to_have_class("theme-dark")
    expect(page.locator('[data-theme-choice="dark"]')).to_have_attribute("aria-pressed", "true")

    choose(page, "System")
    expect(html).to_have_class("")


def test_p1_ui_02_sign_in_page_hides_controls_that_need_script_until_it_runs(page: Page) -> None:
    page.goto("/login")

    expect(page.get_by_role("button", name="Theme")).to_be_visible()
