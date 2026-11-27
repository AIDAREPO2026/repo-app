# Templates

Jinja2 templates, one folder per module (for example `templates/content/`), plus `base.html` and shared components such as `components/endorsed_badge.html`. Every page extends `base.html` (skip link, header, menu for the login type, flash messages, `main`, footer). Buttons, cards, badges, alerts, dialogs, empty states and pagination come from `macros/ui.html` (see them all at `/_styleguide`), form fields from `macros/forms.html`, and the menus from `app/core/navigation.py`. No inline styles, scripts or one-off colours: a test fails on them. Wrap every user-facing string in `_()`.

Autoescaping stays on. Never use `|safe` or `Markup()` on user text.
