"""Turn a browser's User-Agent into a short name, for the Signed-in devices page (P1-ACC-07)."""

# Checked in order: Edge and Opera also say "Chrome", and Chrome also says "Safari".
BROWSERS = (
    ("Edg/", "Edge"),
    ("OPR/", "Opera"),
    ("Firefox/", "Firefox"),
    ("Chrome/", "Chrome"),
    ("Safari/", "Safari"),
)
# Android also says "Linux", and iPhones and iPads also say "Mac OS X".
SYSTEMS = (
    ("Windows", "Windows"),
    ("Android", "Android"),
    ("iPhone", "iPhone"),
    ("iPad", "iPad"),
    ("Mac OS X", "Mac"),
    ("Linux", "Linux"),
)


def device_name(user_agent: str) -> str:
    """Return a name such as "Chrome on Windows". The User-Agent is only what the browser claims."""
    browser = _first_match(user_agent, BROWSERS) or "Unknown browser"
    system = _first_match(user_agent, SYSTEMS)
    return f"{browser} on {system}" if system else browser


def _first_match(user_agent: str, names: tuple[tuple[str, str], ...]) -> str:
    for mark, name in names:
        if mark in user_agent:
            return name
    return ""
