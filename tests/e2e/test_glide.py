"""P1-UI-02: menus and select lists share one highlight that moves to the item in use."""

from playwright.sync_api import Locator, Page, expect

from tests.e2e.test_select import form  # noqa: F401  (the sign-in page with extra selects)


def assert_highlight_under(page: Page, popup: str, item: Locator) -> None:
    page.wait_for_timeout(400)  # the slide
    glider = page.locator(f"{popup} > .menu-glider")
    expect(glider).to_have_count(1)
    under, over = glider.bounding_box(), item.bounding_box()
    assert under and over
    assert abs(under["y"] - over["y"]) <= 1 and abs(under["x"] - over["x"]) <= 1


def test_p1_ui_02_select_highlight_follows_keys_and_pointer(form: Page) -> None:  # noqa: F811
    form.get_by_role("button", name="long").click()
    expect(form.get_by_role("combobox", name="Search")).to_be_focused()
    form.keyboard.press("ArrowDown")
    form.keyboard.press("ArrowDown")
    assert_highlight_under(form, "#long-popup", form.get_by_role("option", name="Discom 3", exact=True))

    form.get_by_role("option", name="Discom 5", exact=True).hover()
    assert_highlight_under(form, "#long-popup", form.get_by_role("option", name="Discom 5", exact=True))
