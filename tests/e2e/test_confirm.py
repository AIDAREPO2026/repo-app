"""P1-UI-02: a serious action is only sent after a yes."""

from typing import Any

from playwright.sync_api import Browser, Page, expect

from app.core.templates import templates
from tests.e2e.axe import blocking_violations
from tests.e2e.pages import open_login_with

FORM = (
    '<form id="danger" method="get" action="/login" data-confirm="This removes it." '
    'data-confirm-title="Remove it?" data-confirm-action="Remove">'
    '<input type="hidden" name="done" value="x"><button type="submit">Delete thing</button></form>'
)


def test_p1_ui_02_nothing_is_sent_until_confirmed(page: Page) -> None:
    open_login_with(page, FORM)
    sent: list[str] = []
    page.on("request", lambda request: sent.append(request.url) if "done=x" in request.url else None)
    dialog = page.get_by_role("dialog", name="Remove it?")

    page.get_by_role("button", name="Delete thing").click()
    expect(dialog).to_contain_text("This removes it.")
    assert blocking_violations(page) == []
    dialog.get_by_role("button", name="Cancel").click()
    expect(dialog).to_be_hidden()
    assert sent == []

    page.get_by_role("button", name="Delete thing").click()
    with page.expect_request("**/login?done=x"):
        dialog.get_by_role("button", name="Remove").click()


def test_p1_ui_02_without_script_a_confirming_form_cannot_be_sent(
    browser: Browser, browser_context_args: dict[str, Any]
) -> None:
    button = templates.env.from_string(
        '{% from "macros/ui.html" import button %}{{ button("Delete thing", needs_script=true) }}'
    ).render()
    form = f'<form method="get" action="/login"><input name="done" aria-label="why">{button}</form>'
    context = browser.new_context(**browser_context_args, java_script_enabled=False)
    page = context.new_page()
    open_login_with(page, form)
    sent: list[str] = []
    page.on("request", lambda request: sent.append(request.url) if "done=" in request.url else None)

    expect(page.get_by_role("button", name="Delete thing")).to_have_count(0)
    page.get_by_label("why").fill("x")
    page.get_by_label("why").press("Enter")
    page.wait_for_timeout(500)

    assert sent == []
    context.close()
