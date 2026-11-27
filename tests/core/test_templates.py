from app.core.templates import templates


def render_field(**options: object) -> str:
    """Render the shared form field macro with the given options."""
    macro = templates.env.get_template("macros/forms.html").module.field  # type: ignore[attr-defined]
    return str(macro(**options))


def test_p1_ui_01_field_links_help_and_error() -> None:
    html = render_field(name="email", label="Email address", help="Your work email", error="Enter an email")

    assert '<label for="email"' in html
    assert 'aria-describedby="email-help email-error"' in html
    assert 'id="email-help"' in html
    assert 'id="email-error"' in html
    assert 'aria-invalid="true"' in html


def test_p1_ui_01_field_without_error_is_not_invalid() -> None:
    html = render_field(name="email", label="Email address")

    assert "aria-describedby" not in html
    assert "aria-invalid" not in html


def test_p1_ui_01_templates_escape_user_text() -> None:
    html = render_field(name="email", label="Email address", value='"><script>alert(1)</script>')

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
