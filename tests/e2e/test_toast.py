"""P1-UI-02: notifications show at the bottom centre and can be closed.

The sign-in page is served with a toast added to it, so the test needs no login.
"""

import re

from playwright.sync_api import Page, Route, expect

TOAST = (
    '<div class="toasts" role="status"><div class="toast toast-success">'
    '<p class="toast-text">Saved</p>'
    '<button type="button" data-toast-close aria-label="Dismiss notification">x</button>'
    '<span class="toast-timer"></span></div></div>'
)


def with_toast(page: Page) -> None:
    def add_toast(route: Route) -> None:
        response = route.fetch()
        route.fulfill(response=response, body=response.text().replace("</body>", TOAST + "</body>"))

    page.route("**/login", add_toast)
    page.goto("/login")


def test_p1_ui_02_a_toast_closes_from_its_button(page: Page) -> None:
    with_toast(page)

    page.get_by_role("button", name="Dismiss notification").click()

    expect(page.locator(".toast")).to_have_count(0)


def test_p1_ui_02_a_success_toast_closes_by_itself(page: Page) -> None:
    with_toast(page)

    expect(page.locator(".toast")).to_have_count(1)
    expect(page.locator(".toast")).to_have_count(0, timeout=8_000)


def test_p1_ui_02_the_result_leaves_the_address_once_shown(page: Page) -> None:
    page.goto("/login?done=added&next=/dashboard/admin")

    expect(page).to_have_url(re.compile(r"/login\?next=[^&]*$"))
