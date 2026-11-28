"""P1-UI-02: rows can be ticked, copied or exported, and have their own right-click menu.

The sign-in page is served with a small table added to it, so the test needs no login.
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page, Route, expect

from app.core.templates import templates
from tests.e2e.axe import blocking_violations

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
    def add_table(route: Route) -> None:
        response = route.fetch()
        extra = TABLE.render() + '<div class="toasts" role="status"></div></main>'
        route.fulfill(response=response, body=response.text().replace("</main>", extra))

    page.route("**/login", add_table)
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("/login")
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
    assert box["width"] <= 220 and box["height"] <= 130  # compact

    menu.get_by_role("button", name="Select row").click()
    expect(table.get_by_role("checkbox", name="Select North")).to_be_checked()
