import re

from playwright.sync_api import Page, expect


def test_p0_qa_02_portal_opens(page: Page) -> None:
    # The public home page arrives in Phase 3 and sign-in in P1-ACC-06. Until then the
    # error page is the only page a visitor can open, and it uses the full base layout.
    page.goto("/no-such-page")

    expect(page).to_have_title(re.compile("Page not found"))
    expect(page.get_by_role("main")).to_be_visible()


def test_p1_acc_08_protected_page_sends_visitor_to_sign_in(page: Page) -> None:
    page.goto("/dashboard/member")

    expect(page).to_have_url(re.compile(r"/login\?next=/dashboard/member$"))
