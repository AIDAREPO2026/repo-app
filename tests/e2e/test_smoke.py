import re

from playwright.sync_api import Page, expect


def test_p0_qa_02_portal_opens(page: Page) -> None:
    # The public home page arrives in Phase 3; until then the Member dashboard shell is the first page.
    page.goto("/dashboard/member")

    expect(page).to_have_title(re.compile("Member dashboard"))
    expect(page.get_by_role("main")).to_be_visible()
