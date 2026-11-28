"""The one Jinja environment every page renders through."""

from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.core.time import to_ist

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"

# Jinja2Templates turns autoescaping on for .html files; never switch it off (security.md).
templates = Jinja2Templates(directory=TEMPLATE_DIR)
templates.env.add_extension("jinja2.ext.i18n")
# SRS 5.5: every string goes through _() now, so Hindi only needs a catalogue later.
# The i18n extension adds this method at runtime, so the type stubs do not know it.
templates.env.install_null_translations(newstyle=True)  # type: ignore[attr-defined]
# Every time shown on a page or in an email is in India Standard Time: {{ moment|ist }}.
templates.env.filters["ist"] = lambda moment: to_ist(moment).strftime("%d %b %Y, %H:%M IST")
