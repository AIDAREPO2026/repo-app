"""P1-ACC-02: the registration page suggests User IDs from the Discom and email, without asking the server.

The real page is served with one made-up Discom added, so the test needs no data.
"""

import re

from playwright.sync_api import Page, Route, expect

from tests.e2e.axe import blocking_violations


def open_register(page: Page) -> None:
    def add_discom(route: Route) -> None:
        response = route.fetch()
        option = '<option value="1">North Power Company (NPCX)</option></select>'
        route.fulfill(response=response, body=response.text().replace("</select>", option, 1))

    page.route("**/register", add_discom)
    page.goto("/register")


def test_fr_1_1_user_ids_are_suggested_and_picked(page: Page) -> None:
    open_register(page)
    group = page.get_by_role("group", name=re.compile("Suggested User IDs"))
    expect(group).to_be_hidden()
    sent: list[str] = []
    page.on("request", lambda request: sent.append(request.url))

    page.get_by_role("button", name=re.compile("^Discom")).click()
    page.get_by_role("option", name="North Power Company (NPCX)").click()
    page.get_by_label("Official email address").fill("Asha.Rao+work@north.example")

    expect(group.get_by_role("button")).to_have_text(["asha.raowork", "npcx.asha.raowork", "npcx.portal"])
    assert blocking_violations(page) == []

    group.get_by_role("button", name="npcx.portal").click()
    expect(page.get_by_label("User ID", exact=False).first).to_have_value("npcx.portal")
    assert [url for url in sent if "/static/" not in url and "/captcha/" not in url] == []
