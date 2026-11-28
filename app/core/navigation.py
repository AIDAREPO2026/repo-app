"""The navigation menu for each login type, kept in one place for the base layout."""

from typing import NamedTuple


class NavLink(NamedTuple):
    """One menu entry. The label is an English message id, translated by the template.

    The icon names one of the drawings in templates/macros/icons.html.
    """

    label: str
    path: str
    icon: str = "grid"
    # The menu section it sits under. The sidebar prints the name where a section starts.
    group: str = "Overview"


# Visitors and error pages see the public menu. Later tasks add entries here, not in templates.
PUBLIC_NAV: list[NavLink] = []

# P1-UI-02: privileged logins review the design system; Members never see it.
STYLE_GUIDE = NavLink("Style guide", "/_styleguide", "swatch", "Resources")
# P1-ACC-10: every login can see its MFA settings.
SECURITY = NavLink("Security", "/account/security", "shield", "Your account")

NAV_BY_LOGIN_TYPE: dict[str, list[NavLink]] = {
    "member": [NavLink("Dashboard", "/dashboard/member"), SECURITY],
    "admin": [
        NavLink("Dashboard", "/dashboard/admin"),
        NavLink("Accounts", "/admin/accounts", "users", "Administration"),
        NavLink("Discoms", "/admin/discoms", "building", "Administration"),
        SECURITY,
        STYLE_GUIDE,
    ],
    "reviewer": [NavLink("Dashboard", "/dashboard/reviewer"), SECURITY, STYLE_GUIDE],
    "approver": [NavLink("Dashboard", "/dashboard/approver"), SECURITY, STYLE_GUIDE],
}


class Crumb(NamedTuple):
    """One step in the breadcrumb trail. The current page has no path."""

    label: str
    path: str | None = None
    # Filled by breadcrumbs() for pages that are in the menu, so both show the same drawing.
    icon: str = ""


def breadcrumbs(login_type: str, *pages: Crumb) -> list[Crumb]:
    """Return the trail from the login's dashboard to the current page, which is the last crumb.

    Pass the pages below the dashboard in order, for example
    `breadcrumbs("admin", Crumb("Accounts", "/admin/accounts"), Crumb("Asha Rao"))`.
    """
    home = NAV_BY_LOGIN_TYPE[login_type][0]
    trail = [Crumb(home.label, home.path), *pages]
    # The last crumb is where the reader is, so it is never a link.
    trail[-1] = Crumb(trail[-1].label)
    icons = {link.label: link.icon for link in NAV_BY_LOGIN_TYPE[login_type]}
    return [crumb._replace(icon=icons.get(crumb.label, "")) for crumb in trail]


def nav_for(login_type: str | None) -> list[NavLink]:
    """Return the menu for a login type, or the public menu for visitors."""
    if login_type is None:
        return PUBLIC_NAV
    return NAV_BY_LOGIN_TYPE[login_type]
