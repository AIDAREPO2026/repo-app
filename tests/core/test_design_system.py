"""P1-UI-02: pages use only the design system: tokens and components, no one-off styles."""

import re
from pathlib import Path

import pytest
from starlette.requests import Request

from app.core.navigation import Crumb, breadcrumbs, nav_for
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


def test_p1_ui_02_breadcrumbs_open_menus_and_mark_the_current_page() -> None:
    template = templates.env.from_string(
        '{% from "macros/ui.html" import breadcrumbs with context %}{{ breadcrumbs(trail, nav) }}'
    )
    request = Request({"type": "http", "path": "/admin/discoms", "headers": [], "query_string": b""})
    trail = breadcrumbs("admin", Crumb("Discoms"))

    html = template.render(request=request, trail=trail, nav=nav_for("admin"))

    assert '<nav aria-label="Breadcrumb">' in html
    assert 'popovertarget="crumb-home"' in html
    assert 'popovertarget="crumb-section"' in html  # Discoms sits in Administration
    assert '<span class="crumb-current" aria-current="page">Discoms</span>' in html


def test_p1_ui_02_theme_button_toggles_and_is_hidden_without_script() -> None:
    macro = templates.env.get_template("macros/ui.html").module.theme_switcher  # type: ignore[attr-defined]

    html = str(macro())

    assert '<div class="theme-switcher" hidden>' in html
    assert "data-theme-toggle" in html
    assert "popovertarget" not in html  # one click changes the theme, with no menu


def test_p1_ui_02_data_table_names_its_scroll_area_and_counts_rows() -> None:
    template = templates.env.from_string(
        '{% from "macros/ui.html" import data_table %}'
        '{% call data_table("Discoms", 3, search="Search Discoms") %}<tbody></tbody>{% endcall %}'
    )

    html = template.render()

    assert 'role="region" aria-label="Discoms" tabindex="0"' in html
    assert 'aria-label="Search Discoms"' in html
    assert "<span data-shown>3</span> / 3" in html


def test_p1_ui_02_controls_shrink_only_while_pressed() -> None:
    # A damaged selector list once left every button and link permanently scaled down.
    css = re.sub(r"/\*.*?\*/", "", COMPONENTS_CSS, flags=re.S)
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        if "transform: scale(var(--aida-press-scale" in body and "from" not in selectors:
            assert all(":active" in part for part in selectors.split(",")), selectors.strip()


def test_p1_ui_02_every_button_has_an_icon() -> None:
    calls = [
        (template.name, call)
        for template in TEMPLATES
        for call in re.findall(r"\{\{ (?:link_)?button\(.*?\) \}\}", template.read_text())
    ]

    assert calls
    assert [item for item in calls if "icon_name=" not in item[1]] == []


def test_p1_ui_02_select_renders_a_native_select_that_script_enhances() -> None:
    template = templates.env.from_string(
        '{% from "macros/forms.html" import select %}'
        '{{ select("discom", "Discom", [(1, "North"), (2, "South")], value=2, source="/lookup") }}'
    )

    html = template.render()

    assert 'data-select data-source="/lookup"' in html
    assert '<select id="discom" name="discom" class="input"' in html
    assert '<option value="2" selected>South</option>' in html
