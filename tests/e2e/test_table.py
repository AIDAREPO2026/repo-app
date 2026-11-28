"""P1-UI-02: rows can be ticked, copied or exported, and have their own right-click menu.

The sign-in page is served with a small table added to it, so the test needs no login.
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from app.core.templates import templates
from tests.e2e.axe import blocking_violations
from tests.e2e.pages import open_login_with

TABLE = templates.env.from_string(
    '{% from "macros/ui.html" import data_table %}'
    '{% call data_table("Discoms", 2, columns=["Discom", "Domain"],'
    ' copy_label="Copy domain", file="discoms") %}'
    "<thead><tr><th>Discom</th></tr></thead><tbody>"
    """<tr data-export='["North", "north.example"]' data-copy="north.example"><td>North</td></tr>"""
    """<tr data-export='["=HYPERLINK(1)", "b.example"]' data-copy="b.example"><td>Formula</td></tr>"""
    "</tbody>{% endcall %}"
)


@pytest.fixture
def table(page: Page) -> Page:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    open_login_with(page, TABLE.render() + '<div class="toasts" role="status"></div>')
    page.wait_for_load_state()
    assert errors == []  # the table's attributes must not wake another script
    return page


def test_p1_ui_02_ticked_rows_show_actions_and_export_safely(table: Page, tmp_path: Path) -> None:
    bar = table.get_by_role("toolbar", name="Selected rows")
    expect(bar).to_be_hidden()

    table.get_by_role("checkbox", name="Select all rows shown").check()
    expect(bar).to_be_visible()
    expect(bar).to_contain_text("2 selected")
    assert blocking_violations(table) == []
    box, window = bar.bounding_box(), table.viewport_size
    assert box and window
    assert abs(box["x"] + box["width"] / 2 - window["width"] / 2) <= 2  # centred on the page

    with table.expect_download() as download:
        table.get_by_role("button", name="Export CSV").click()
    saved = tmp_path / "rows.csv"
    download.value.save_as(saved)
    text = saved.read_text(encoding="utf-8-sig")
    assert text.splitlines()[0] == '"Discom","Domain"'
    assert '"\'=HYPERLINK(1)"' in text  # a spreadsheet must not run it as a formula

    table.get_by_role("button", name="Clear selection").click()
    expect(bar).to_be_hidden()


def test_p1_ui_02_right_click_opens_the_row_menu_inside_the_window(table: Page) -> None:
    row = table.get_by_role("row", name="North")
    row.click(button="right")
    menu = table.get_by_role("group", name="Row actions")
    expect(menu).to_be_visible()

    box = menu.bounding_box()
    window = table.viewport_size
    assert box and window
    assert box["x"] + box["width"] <= window["width"] and box["y"] + box["height"] <= window["height"]

    # One highlight: the arrow keys move it, and so does the pointer.
    table.keyboard.press("ArrowDown")
    expect(menu.get_by_role("button", name="Select row")).to_be_focused()
    menu.get_by_role("button", name="Copy domain").hover()
    expect(menu.get_by_role("button", name="Copy domain")).to_be_focused()
    assert box["width"] <= 260 and box["height"] <= 170  # roomy, not sprawling
    # The one highlight has slid under the item in use.
    copy_item = menu.get_by_role("button", name="Copy domain").bounding_box()
    glider = table.locator(".menu-glider")
    table.wait_for_timeout(400)
    under = glider.bounding_box()
    assert copy_item and under and abs(under["y"] - copy_item["y"]) <= 1

    menu.get_by_role("button", name="Select row").click()
    expect(table.get_by_role("checkbox", name="Select North")).to_be_checked()


def test_p1_ui_02_long_table_shows_more_rows_as_it_scrolls(page: Page) -> None:
    long_table = templates.env.from_string(
        '{% from "macros/ui.html" import data_table %}'
        '{% call data_table("Words", 120, search="Search words", compact=true, batch=50) %}'
        "<tbody>{% for n in range(120) %}<tr><td>word {{ n }}</td></tr>{% endfor %}</tbody>{% endcall %}"
    )
    open_login_with(page, long_table.render())
    shown = page.locator("[data-shown]")
    expect(shown).to_have_text("50")

    page.locator("tbody tr:not([hidden])").last.scroll_into_view_if_needed()
    expect(shown).not_to_have_text("50")
    for _ in range(4):
        page.locator("tbody tr:not([hidden])").last.scroll_into_view_if_needed()
    expect(shown).to_have_text("120")

    # A search covers every row, including ones that had not been shown yet.
    page.get_by_label("Search words").fill("word 119")
    expect(shown).to_have_text("1")


def test_p1_ui_02_table_filters_by_group_and_search_together(page: Page) -> None:
    grouped = templates.env.from_string(
        '{% from "macros/ui.html" import data_table %}'
        '{% call data_table("Words", 3, search="Search words", batch=2,'
        ' groups=["Web", "Pages"], group_label="Category") %}'
        '<tbody><tr data-group="Web"><td>ftp</td></tr><tr data-group="Pages"><td>login</td></tr>'
        '<tr data-group="Web"><td>www</td></tr></tbody>{% endcall %}'
    )
    open_login_with(page, grouped.render())
    shown = page.locator("[data-shown]")

    page.get_by_role("button", name="Category").click()
    page.get_by_role("option", name="Web").click()
    expect(shown).to_have_text("2")
    expect(page.get_by_role("row", name="login")).to_have_count(0)

    page.get_by_label("Search words").fill("www")
    expect(shown).to_have_text("1")

    page.get_by_label("Search words").fill("")
    page.get_by_role("button", name="Category").click()
    page.get_by_role("option", name="All").click()
    expect(page.locator("tbody tr:not([hidden])")).to_have_count(3)  # scrolled into view, so all show
