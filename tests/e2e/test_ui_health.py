"""P1-UI-02: no page may ship with a script error, sideways scroll, or a stuck pressed state.

These run on the pages anyone can open. Add each new public page to PAGES. Signed-in pages
need the seeded e2e logins (P0-QA-02) and are checked once those exist.
"""

import pytest
from playwright.sync_api import Page

PAGES = ["/login", "/register", "/no-such-page"]
WIDTHS = [1280, 375]

# Controls sitting at a scaled size with nothing pressing them.
STUCK = """() => [...document.querySelectorAll('a, button, summary')]
  .filter(e => /^matrix\\((?!1, 0, 0, 1)/.test(getComputedStyle(e).transform))
  .map(e => e.outerHTML.slice(0, 80))"""


@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("path", PAGES)
def test_p1_ui_02_page_is_healthy(page: Page, path: str, width: int) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(path)
    page.wait_for_load_state()

    assert errors == []
    assert page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") == 0
    assert page.evaluate(STUCK) == []
