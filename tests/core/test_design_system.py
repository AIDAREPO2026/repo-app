"""P1-UI-02: pages use only the design system: tokens and components, no one-off styles."""

import re
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
TEMPLATES = sorted((APP_DIR / "templates").rglob("*.html"))
COMPONENTS_CSS = (APP_DIR / "static" / "css" / "components.css").read_text()

# Tailwind's own palette (switched off in app.src.css) and arbitrary values such as w-[13px].
ONE_OFF_CLASS = re.compile(
    r"\b(?:bg|text|border|ring|fill|stroke|from|to|via)-"
    r"(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|"
    r"indigo|violet|purple|fuchsia|pink|rose|white|black)\b|-\[[^\]]+\]"
)


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda path: path.name)
def test_p1_ui_02_templates_use_only_design_tokens(template: Path) -> None:
    html = template.read_text()

    assert "style=" not in html
    assert "<script" not in html
    assert ONE_OFF_CLASS.findall(html) == []


def test_p1_ui_02_components_animate_only_transform_and_opacity() -> None:
    allowed = {"transform", "opacity", "overlay", "display"}
    for declaration in re.findall(r"transition:\s*([^;]+);", COMPONENTS_CSS):
        properties = {part.split()[0] for part in declaration.split(",")}
        assert properties <= allowed, declaration
