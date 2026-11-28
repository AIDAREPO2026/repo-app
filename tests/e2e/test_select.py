"""P1-UI-02: the select box searches long lists, loads pages from a server and opens where it fits.

The sign-in page is served with extra selects added to it, and the server's answers are
made up here, so the tests need no login and change nothing.
"""

import json
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import Page, Route, expect

from tests.e2e.axe import blocking_violations
from tests.e2e.pages import open_login_with


def native(field_id: str, options: int, source: str = "") -> str:
    """Return the markup macros/forms.html renders, with numbered options."""
    items = "".join(f'<option value="{n}">Discom {n}</option>' for n in range(1, options + 1))
    remote = f' data-source="{source}"' if source else ""
    return (
        f'<div class="field" data-select{remote} data-placeholder="Choose" data-search="Search" '
        'data-loading="Loading" data-empty="No matches" data-failed="Failed">'
        f'<label for="{field_id}" id="{field_id}-label">{field_id}</label>'
        f'<select id="{field_id}" name="{field_id}" class="input">'
        f'<option value="">Choose</option>{items}</select></div>'
    )


def answer_options(route: Route) -> None:
    """Pages of 20 made-up records, three pages in all, filtered by q."""
    query = parse_qs(urlsplit(route.request.url).query)
    text, number = query.get("q", [""])[0], int(query["page"][0])
    names = [f"Record {n}" for n in range(1, 61) if text in str(n)]
    start = (number - 1) * 20
    items = [{"value": name, "label": name} for name in names[start : start + 20]]
    body = json.dumps({"items": items, "more": start + 20 < len(names)})
    route.fulfill(body=body, content_type="application/json")


@pytest.fixture
def form(page: Page) -> Page:
    extra = native("short", 3) + native("long", 15) + native("remote", 0, "/fake-options")

    page.route("**/fake-options?*", answer_options)
    open_login_with(page, extra)
    return page


def test_p1_ui_02_hidden_select_takes_no_room(form: Page) -> None:
    box = form.locator("#long").bounding_box()
    sideways = form.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")

    assert box and box["width"] <= 1
    assert sideways == 0


def test_p1_ui_02_search_appears_only_above_ten_options(form: Page) -> None:
    form.get_by_role("button", name="short").click()
    expect(form.get_by_role("listbox", name="short")).to_be_focused()
    expect(form.get_by_role("combobox", name="Search")).to_have_count(0)
    form.keyboard.press("ArrowDown")
    form.keyboard.press("Enter")
    expect(form.locator("#short")).to_have_value("2")

    form.get_by_role("button", name="long").click()
    form.get_by_role("combobox", name="Search").fill("15")
    expect(form.get_by_role("option")).to_have_count(1)
    assert blocking_violations(form) == []
    form.keyboard.press("Enter")
    expect(form.locator("#long")).to_have_value("15")


def test_p1_ui_02_server_options_load_page_by_page_and_search(form: Page) -> None:
    form.get_by_role("button", name="remote").click()
    expect(form.get_by_role("option")).to_have_count(20)

    form.get_by_role("listbox").evaluate("list => list.scrollTop = list.scrollHeight")
    expect(form.get_by_role("option")).to_have_count(40)

    form.get_by_role("combobox", name="Search").fill("59")
    expect(form.get_by_role("option")).to_have_count(1)
    form.get_by_role("option", name="Record 59").click()
    expect(form.locator("#remote")).to_have_value("Record 59")


def test_p1_ui_02_list_opens_upward_when_there_is_no_room_below(form: Page) -> None:
    form.set_viewport_size({"width": 900, "height": 600})
    button = form.get_by_role("button", name="long")
    # Put the button near the bottom edge of the window.
    button.evaluate("b => window.scrollBy(0, b.getBoundingClientRect().bottom - window.innerHeight + 8)")
    button.click()

    popup = form.locator("#long-popup").bounding_box()
    anchor = button.bounding_box()
    assert popup and anchor
    assert popup["y"] + popup["height"] <= anchor["y"] + 1
