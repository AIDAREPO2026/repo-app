"""Serve a real page with extra markup in it, for browser tests that need no login."""

from playwright.sync_api import Page, Route


def open_login_with(page: Page, markup: str, before: str = "</main>") -> None:
    """Open the sign-in page with markup inserted just before the given closing tag."""

    def add_markup(route: Route) -> None:
        response = route.fetch()
        route.fulfill(response=response, body=response.text().replace(before, markup + before))

    page.route("**/login", add_markup)
    page.goto("/login")
