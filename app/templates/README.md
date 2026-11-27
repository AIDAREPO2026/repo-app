# Templates

Jinja2 templates, one folder per module (for example `templates/content/`), plus `base.html` and shared components such as `components/endorsed_badge.html`. The base layout arrives in `P1-UI-01`.

Autoescaping stays on. Never use `|safe` or `Markup()` on user text.
