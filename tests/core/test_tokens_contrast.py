"""P1-UI-02: every colour pair the components use meets WCAG 2.1 AA, in light and dark (SRS 5.5).

The pairs are read from static/css/tokens.css itself, so changing a colour that breaks
contrast fails here before anyone sees it.
"""

import re
from pathlib import Path

import pytest

TOKENS_CSS = (Path(__file__).resolve().parents[2] / "app" / "static" / "css" / "tokens.css").read_text()
# Only the :root block: the accessibility media queries below it change some tokens again.
ROOT_BLOCK = TOKENS_CSS[TOKENS_CSS.index(":root {") : TOKENS_CSS.index("\n}\n")]
TOKEN = re.compile(r"--aida-([a-z0-9-]+):\s*([^;]+);")
LIGHT_DARK = re.compile(r"light-dark\((#[0-9a-f]{6}),\s*(#[0-9a-f]{6})\)")
REFERENCE = re.compile(r"var\(--aida-([a-z0-9-]+)\)")

TEXT = 4.5  # WCAG 1.4.3 for normal-size text
UI = 3.0  # WCAG 1.4.11 for field borders and the focus ring

SURFACES = ("canvas", "surface", "surface-sunken", "surface-hover")
PAIRS = [
    *[("text", surface, TEXT) for surface in (*SURFACES, "surface-pressed")],
    *[("text-muted", surface, TEXT) for surface in SURFACES],
    # Links, the current menu entry and accent badges.
    *[("accent", surface, TEXT) for surface in (*SURFACES, "accent-subtle")],
    # Primary buttons at rest, hovered and pressed.
    *[("accent-contrast", fill, TEXT) for fill in ("accent", "accent-hover", "accent-pressed")],
    # Form fields: inputs, select boxes and checkboxes must be visible against their page.
    *[("border-strong", surface, UI) for surface in ("canvas", "surface")],
    *[("focus-ring", surface, UI) for surface in ("canvas", "surface", "surface-sunken")],
    # Alerts, badges and the danger button.
    *[(status, f"{status}-subtle", TEXT) for status in ("success", "warning", "danger")],
    *[(status, "surface", TEXT) for status in ("success", "warning", "danger")],
    ("danger-hover", "danger-subtle", TEXT),
    ("on-amber", "brand-amber", TEXT),
    # The navy sidebar, menu drawer and sign-in brand panel.
    *[("chrome-text", fill, TEXT) for fill in ("chrome", "chrome-hover", "chrome-active")],
    ("chrome-label", "chrome", TEXT),
    ("chrome-strong", "chrome-active", TEXT),
    *[("chrome-focus", fill, UI) for fill in ("chrome", "chrome-active")],
]


def tokens() -> dict[str, str]:
    """Return each token's raw value from the :root block."""
    return dict(TOKEN.findall(ROOT_BLOCK))


def colour(name: str, theme: int) -> str:
    """Return a token's hex colour for the light (0) or dark (1) theme, following var() links."""
    value = tokens()[name].strip()
    reference = REFERENCE.fullmatch(value)
    if reference:
        return colour(reference.group(1), theme)
    both = LIGHT_DARK.fullmatch(value)
    if both:
        return both.group(theme + 1)
    return value


def luminance(hex_colour: str) -> float:
    """Return the WCAG relative luminance of a #rrggbb colour."""
    channels = [int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(first: str, second: str) -> float:
    """Return the WCAG contrast ratio between two colours."""
    lighter, darker = sorted((luminance(first), luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("theme", [0, 1], ids=["light", "dark"])
@pytest.mark.parametrize(("foreground", "background", "minimum"), PAIRS)
def test_p1_ui_02_token_pairs_meet_wcag_aa(
    foreground: str, background: str, minimum: float, theme: int
) -> None:
    ratio = contrast(colour(foreground, theme), colour(background, theme))

    assert ratio >= minimum, f"{foreground} on {background}: {ratio:.2f}"
