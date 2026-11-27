# Templates

Jinja2 templates, one folder per module (for example `templates/content/`), plus `base.html` and shared components such as `components/endorsed_badge.html`. Every page extends `base.html` (skip link, header, menu for the login type, flash messages, `main`, footer). Form fields come from `macros/forms.html`, and the menus from `app/core/navigation.py`. Wrap every user-facing string in `_()`.

Autoescaping stays on. Never use `|safe` or `Markup()` on user text.
