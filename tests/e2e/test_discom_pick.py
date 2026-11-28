"""P1-ACC-01: picking a Discom from the draft list fills the form and asks for confirmation again."""

from playwright.sync_api import Page, expect

from tests.e2e.pages import open_login_with

FORM = (
    '<form><div data-fill-discom="add-"><div class="field" data-select data-placeholder="Search" '
    'data-search="Search" data-loading="Loading" data-empty="No matches" data-failed="Failed">'
    '<label for="add-suggestion" id="add-suggestion-label">Find the Discom</label>'
    '<select id="add-suggestion" class="input"><option value="">Search</option>'
    '<option value="North Power|north.example">North Power</option>'
    '<option value="South Power|">South Power</option>'
    # More than ten options, so the dropdown has its search box, as the real list does.
    + "".join(f'<option value="Other {n}|o{n}.example">Other {n}</option>' for n in range(10))
    + "</select></div></div>"
    '<input id="add-name" aria-label="name"><input id="add-email_domain" aria-label="domain">'
    '<input type="checkbox" name="checked" aria-label="checked"></form>'
)


def pick(page: Page, name: str) -> None:
    """Search for a Discom and choose it with Enter, as a person typing would."""
    page.get_by_role("button", name="Find the Discom").click()
    search = page.get_by_role("combobox", name="Search")
    expect(search).to_be_focused()
    search.fill(name.split()[0].lower())
    page.keyboard.press("Enter")


def test_fr_1_6_picking_a_discom_fills_the_form(page: Page) -> None:
    open_login_with(page, FORM)
    page.get_by_role("checkbox", name="checked").check()

    pick(page, "North Power")

    expect(page.locator("#add-name")).to_have_value("North Power")
    expect(page.locator("#add-email_domain")).to_have_value("north.example")
    expect(page.get_by_role("checkbox", name="checked")).not_to_be_checked()

    pick(page, "South Power")

    expect(page.locator("#add-email_domain")).to_have_value("")  # never keeps the last one's domain
