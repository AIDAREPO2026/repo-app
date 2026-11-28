"""P1-ACC-02 in a real browser: the registration page is accessible and its CAPTCHA works under the CSP.

Nothing is submitted, so the target database is unchanged.
"""

import pytest
from playwright.sync_api import Page, expect

from tests.e2e.axe import blocking_violations


@pytest.mark.parametrize("scheme", ["light", "dark"])
def test_p1_acc_02_registration_page_accessible(page: Page, scheme: str) -> None:
    page.emulate_media(color_scheme=scheme)
    page.goto("/register")

    expect(page.get_by_role("heading", name="Privacy notice")).to_be_visible()
    assert blocking_violations(page) == []


def test_fr_1_2_captcha_widget_solves_challenge(page: Page) -> None:
    page.goto("/register")

    # The label, as a person would: the widget draws its tick icon over the input itself.
    page.locator("altcha-widget label", has_text="I’m not a robot").click()

    # The widget fetches our challenge and solves it in a worker from /static/, so this
    # passing shows the strict CSP lets it run.
    expect(page.locator("altcha-widget input[name='altcha']")).not_to_have_value("", timeout=15_000)
