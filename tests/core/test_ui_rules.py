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
    for texts in (router.DONE_MESSAGES, router.DISCOM_DONE_MESSAGES):
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
