"""The navigation menu for each login type, kept in one place for the base layout."""

from typing import NamedTuple


class NavLink(NamedTuple):
    """One menu entry. The label is an English message id, translated by the template."""

    label: str
    path: str


# Visitors and error pages see the public menu. Later tasks add entries here, not in templates.
PUBLIC_NAV: list[NavLink] = []

NAV_BY_LOGIN_TYPE: dict[str, list[NavLink]] = {
    "member": [NavLink("Dashboard", "/dashboard/member")],
    "admin": [NavLink("Dashboard", "/dashboard/admin")],
    "reviewer": [NavLink("Dashboard", "/dashboard/reviewer")],
    "approver": [NavLink("Dashboard", "/dashboard/approver")],
}


def nav_for(login_type: str | None) -> list[NavLink]:
    """Return the menu for a login type, or the public menu for visitors."""
    if login_type is None:
        return PUBLIC_NAV
    return NAV_BY_LOGIN_TYPE[login_type]
