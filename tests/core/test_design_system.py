"""P1-UI-02: pages use only the design system: tokens and components, no one-off styles."""

import re
from pathlib import Path

import pytest

from app.core.navigation import Crumb, breadcrumbs
from app.core.templates import templates

APP_DIR = Path(__file__).resolve().parents[2] / "app"
TEMPLATES = sorted((APP_DIR / "templates").rglob("*.html"))
COMPONENTS_CSS = (APP_DIR / "static" / "css" / "components.css").read_text()

# Tailwind's own palette (switched off in app.src.css) and arbitrary values such as w-[13px].
ONE_OFF_CLASS = re.compile(
    r"\b(?:bg|text|border|ring|fill|stroke|from|to|via)-"
    r"(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|"
    r"indigo|violet|purple|fuchsia|pink|rose|white|black)\b|-\[[^\]]+\]"
)

# architecture.md: self-hosted scripts only, never inline. A <script> must load a file by src.
INLINE_SCRIPT = re.compile(r"<script(?![^>]*\bsrc=)")


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda path: path.name)
def test_p1_ui_02_templates_use_only_design_tokens(template: Path) -> None:
    html = template.read_text()

    assert "style=" not in html
    assert INLINE_SCRIPT.findall(html) == []
    assert ONE_OFF_CLASS.findall(html) == []


def test_p1_ui_02_components_animate_only_transform_and_opacity() -> None:
    allowed = {"transform", "opacity", "overlay", "display"}
    for declaration in re.findall(r"transition:\s*([^;]+);", COMPONENTS_CSS):
        properties = {part.split()[0] for part in declaration.split(",")}
        assert properties <= allowed, declaration


def test_p1_ui_02_breadcrumbs_start_at_the_dashboard_and_end_unlinked() -> None:
    trail = breadcrumbs("admin", Crumb("Accounts", "/admin/accounts"), Crumb("Asha Rao", "/ignored"))

    assert trail == [
        Crumb("Dashboard", "/dashboard/admin"),
        Crumb("Accounts", "/admin/accounts"),
        Crumb("Asha Rao"),
    ]


def test_p1_ui_02_breadcrumbs_markup_marks_the_current_page() -> None:
    macro = templates.env.get_template("macros/ui.html").module.breadcrumbs  # type: ignore[attr-defined]

    html = str(macro(breadcrumbs("reviewer", Crumb("Style guide"))))

    assert '<nav aria-label="Breadcrumb">' in html
    assert '<a href="/dashboard/reviewer" class="crumb-link">Dashboard</a>' in html
    assert '<span class="crumb-current" aria-current="page">Style guide</span>' in html


def test_p1_ui_02_theme_switcher_offers_three_choices_hidden_without_script() -> None:
    macro = templates.env.get_template("macros/ui.html").module.theme_switcher  # type: ignore[attr-defined]

    html = str(macro())

    assert re.findall(r'data-theme-choice="(\w+)"', html) == ["system", "light", "dark"]
    assert 'aria-label="Theme" hidden' in html
