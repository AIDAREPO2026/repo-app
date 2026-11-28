"""The UI rules in docs/conventions.md that can be checked without a browser (P1-UI-02).

Each one exists because the mistake it names reached a review. Browser-only rules are in
tests/e2e/test_ui_health.py.
"""

import re
from pathlib import Path

import pytest

from app.accounts import router

APP_DIR = Path(__file__).resolve().parents[2] / "app"
SHELL_JS = (APP_DIR / "static" / "js" / "shell.js").read_text()
ROUTERS = sorted(APP_DIR.glob("*/router.py"))
TEMPLATES = sorted((APP_DIR / "templates").rglob("*.html"))

# A redirect that carries the result of a change in its address: f"{SOME_PATH}?done=..."
RESULT_REDIRECT = re.compile(r'f"\{\w+_PATH\}\?(\w+)=')
TAKES_AWAY = re.compile(r"deactivat|delet|remov|revok|reset|_off$|reject")


def test_p1_ui_02_every_result_in_an_address_is_forgotten_once_shown() -> None:
    names = {name for path in ROUTERS for name in RESULT_REDIRECT.findall(path.read_text())}

    assert names  # or the pattern has stopped matching how results are sent
    forgotten = set(re.findall(r'searchParams\.delete\("(\w+)"\)', SHELL_JS))
    assert names <= forgotten, "add the new result name to forgetResult() in static/js/shell.js"


def test_p1_ui_02_changes_that_take_something_away_are_never_a_plain_success() -> None:
    for texts in (router.DONE_MESSAGES, router.DISCOM_DONE_MESSAGES, router.RESERVED_DONE_MESSAGES):
        for key in texts:
            if TAKES_AWAY.search(key):
                assert router.done_message(key, texts)[0][0] == "warning", key
    for key, (tone, _) in router.SECURITY_DONE.items():
        if TAKES_AWAY.search(key):
            assert tone == "warning", key


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda path: path.name)
def test_p1_ui_02_choices_use_the_select_component(template: Path) -> None:
    if template.name == "forms.html":
        return
    assert "<select" not in template.read_text(), "use select() from macros/forms.html"


def test_p1_ui_02_scripts_never_declare_the_same_top_level_name() -> None:
    # Plain scripts share one scope: a repeated const stops the second file from running at all.
    seen: dict[str, str] = {}
    for script in sorted((APP_DIR / "static" / "js").glob("*.js")):
        names = re.findall(r"^(?:async )?(?:function|const|let|class) (\w+)", script.read_text(), re.M)
        for name in names:
            assert name not in seen, f"{name} is declared in {seen[name]} and {script.name}"
            seen[name] = script.name


# Actions that are not serious: they start or end the person's own session, finish a step they
# are in the middle of, or can be undone at once without changing who may do what.
SAFE_ACTIONS = {
    "/logout", "/login", "/register", "/register/code", "/register/account",
    "/forgot-password", "/{{ link_page }}/{{ token }}",
    "/mfa", "/mfa/setup", "/mfa/send-code", "/mfa/cancel", "/account/security/send-code",
    "/account/security/mfa-on", "/admin/discoms/import/preview", "/admin/reserved-ids",
    "/admin/reserved-ids/restore",
}  # fmt: skip
CONFIRMING_FORM = re.compile(
    r'<form method="post"(?:(?!</form>).)*?data-confirm=(?:(?!</form>).)*</form>', re.S
)
POST_FORM = re.compile(r'<form method="post" action="(.*?)"((?:[^>]|(?<=%)>)*)>', re.S)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda path: path.name)
def test_p1_ui_02_serious_actions_are_confirmed(template: Path) -> None:
    for action, attributes in POST_FORM.findall(template.read_text()):
        confirmed = "data-confirm=" in attributes or "data-confirmed-by=" in attributes
        assert confirmed or action in SAFE_ACTIONS, (
            f"{action}: add data-confirm (see docs/conventions.md), "
            "or add it to SAFE_ACTIONS if it is not serious"
        )


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda path: path.name)
def test_p1_ui_02_a_form_that_asks_cannot_be_sent_without_the_script(template: Path) -> None:
    for form in CONFIRMING_FORM.findall(template.read_text()):
        # button() and dialog_actions() are the two ways a form gets its submit button.
        calls = re.findall(r"\{\{ (?:button|dialog_actions)\(.*?\) \}\}", form)
        submits = [call for call in calls if 'type="button"' not in call]
        assert submits and all("needs_script=true" in call for call in submits), submits


# Each choice list, with what keeps it to choices the service will accept.
OFFERED_CHOICES = {
    (
        "register.html",
        "organisation_id",
    ): "open Discoms only: test_fr_1_6_a_discom_with_a_login_is_not_offered",
    ("admin_accounts.html", "login_type"): "free roles: test_fr_2_7_a_filled_role_is_not_offered",
    ("admin_discoms.html", "suggestion"): "Discoms not yet added; it only fills the form",
    ("admin_reserved_ids.html", "category"): "fixed list, every value accepted",
    ("admin_reserved_ids.html", "where"): "fixed list, every value accepted",
    ("admin_sign_in_rules.html", "policy"): "fixed list, every value accepted",
    ("ui.html", "group"): "only filters the rows of a table",
}


def test_p1_ui_02_every_choice_list_offers_only_what_is_accepted() -> None:
    found = {
        (template.name, name)
        for template in TEMPLATES
        if template.name != "styleguide.html"
        for name in re.findall(r'\{\{ select\("(\w+)"', template.read_text())
    }
    assert found == set(OFFERED_CHOICES), (
        "list the select() in OFFERED_CHOICES with how its choices stay acceptable "
        "(docs/conventions.md, Never offer what will be refused)"
    )
