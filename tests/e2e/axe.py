"""Run the axe accessibility checker in a Playwright page (WCAG 2.1 AA, SRS 5.5)."""

from pathlib import Path

from playwright.sync_api import Page

# Installed by `npm ci`; the version is pinned in package.json.
AXE_SCRIPT = Path(__file__).resolve().parents[2] / "node_modules" / "axe-core" / "axe.min.js"
WCAG_21_AA_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]
# The acceptance criteria allow no serious or critical issues.
BLOCKING_IMPACTS = {"serious", "critical"}
FINITE_ANIMATIONS_DONE = (
    "document.getAnimations()"
    ".every(a => a.playState !== 'running' || a.effect.getTiming().iterations === Infinity)"
)


def blocking_violations(page: Page) -> list[str]:
    """Return one line for each serious or critical WCAG 2.1 AA issue on the page."""
    # Entrance animations fade text in; axe would measure the half-faded colours. Wait for every
    # finite animation to end (the skeleton pulse runs forever and is not text).
    page.wait_for_function(FINITE_ANIMATIONS_DONE)
    # page.evaluate() runs through the browser's debugging channel, so the page's
    # strict CSP does not block the injected script and the CSP stays as in production.
    page.evaluate(AXE_SCRIPT.read_text())
    run_axe = "tags => axe.run(document, {runOnly: {type: 'tag', values: tags}})"
    results = page.evaluate(run_axe, WCAG_21_AA_TAGS)
    problems = []
    for violation in results["violations"]:
        if violation["impact"] in BLOCKING_IMPACTS:
            count = len(violation["nodes"])
            problems.append(f"{violation['id']} ({violation['impact']}): {count} element(s)")
    return problems
