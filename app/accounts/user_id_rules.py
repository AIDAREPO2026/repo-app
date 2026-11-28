"""Which User IDs nobody may choose, and the tricks a refusal has to see through (P1-ACC-02).

Pure text rules. The words themselves are settings an Admin edits (app.core.settings_store);
DEFAULT_ANYWHERE and DEFAULT_PARTS are what they start as.
"""

import re

# Refused wherever they appear in an ID.
DEFAULT_ANYWHERE = (
    "admin", "superuser", "sysadm", "webmaster", "postmaster", "hostmaster", "moderator", "itped",
    "helpdesk", "noreply", "localhost", "official",
)  # fmt: skip

# Refused as the whole ID or as a whole part between . _ and -.
DEFAULT_PARTS = (
    # Authority
    "root", "su", "sudo", "owner", "master", "manager", "director", "chairman", "officer", "staff",
    "team", "mod",
    # Portal
    "aida", "discom", "discoms", "portal", "repository", "member", "reviewer", "approver", "visitor",
    "secretariat", "association",
    # System
    "system", "sys", "service", "daemon", "server", "backup", "database", "db", "operator", "cron",
    "bot", "robot", "api", "app", "dev", "test", "staging", "prod", "git", "log", "logs", "sql",
    # Web and network
    "www", "www1", "web", "http", "https", "ftp", "sftp", "ssh", "ssl", "tls", "dns", "ns1", "ns2",
    "mx", "tcp", "udp", "smtp", "imap", "pop", "pop3", "mail", "email", "webmail", "ldap", "vpn",
    "cdn", "proxy", "host", "domain", "website", "url", "uri", "ip", "cloud",
    # Trust and support
    "support", "help", "security", "secure", "abuse", "contact", "info", "notice", "notification",
    "alert", "billing", "privacy", "legal", "audit", "compliance", "verify", "verified",
    # Pages and actions
    "login", "logout", "signin", "signup", "register", "account", "password", "reset", "dashboard",
    "settings", "profile", "search", "static", "health", "healthz", "captcha", "delete", "update",
    # Government
    "gov", "govt", "government", "ministry", "india", "bharat", "regulator", "cerc", "cea", "pfc",
    "rec", "mop",
    # Placeholders
    "demo", "guest", "user", "anonymous", "unknown", "null", "nil", "undefined", "none", "true",
    "false", "default", "example", "sample", "temp",
)  # fmt: skip

SEPARATORS = re.compile(r"[._-]+")
# Endings that make an ID look like a web address or a file.
ADDRESS_ENDINGS = (".com", ".in", ".org", ".net", ".co", ".gov", ".nic", ".exe", ".php", ".html")
LOOK_ALIKES = {"0": "o", "3": "e", "4": "a", "5": "s", "7": "t"}
# Short words are not matched with doubled letters removed, or "appu" would be read as "app".
SQUEEZE_FROM = 4


def shape_problem(user_id: str) -> str:
    """Return why the ID has a shape that is not allowed, or "" when its shape is fine."""
    if not re.fullmatch(r"[a-z].*[a-z0-9]", user_id):
        return "Start with a letter and end with a letter or number."
    if re.search(r"[._-]{2}", user_id):
        return "Do not put two of . _ - next to each other."
    if len(re.findall(r"[a-z]", user_id)) < 3:
        return "Use at least 3 letters."
    if user_id.endswith(ADDRESS_ENDINGS):
        return "Do not end like a web address or a file name, such as .com or .in."
    return ""


def plain_word(text: str) -> str:
    """Return a word as it is stored and compared: lowercase, without separators."""
    return SEPARATORS.sub("", text.strip().lower())


def _disguises(text: str) -> set[str]:
    """Return the ways a word may be hiding: number tails, look-alike digits and plurals."""
    forms = set()
    for base in {text, text.rstrip("0123456789")}:
        forms.add(base)
        # A 1 can stand for an i or an l.
        for one in ("i", "l"):
            swaps: dict[str, str | int | None] = {**LOOK_ALIKES, "1": one}
            forms.add(base.translate(str.maketrans(swaps)))
    return forms | {form[:-1] for form in forms if form.endswith("s")}


def _squeeze(text: str) -> str:
    """Return the text with doubled letters made single."""
    return re.sub(r"(.)\1+", r"\1", text)


def _is_word(forms: set[str], word: str) -> bool:
    if word in forms:
        return True
    return len(_squeeze(word)) >= SQUEEZE_FROM and _squeeze(word) in {_squeeze(form) for form in forms}


def _holds_word(forms: set[str], word: str) -> bool:
    if any(word in form for form in forms):
        return True
    squeezed = _squeeze(word)
    return len(squeezed) >= SQUEEZE_FROM and any(squeezed in _squeeze(form) for form in forms)


def is_reserved(user_id: str, anywhere: list[str], parts: list[str]) -> bool:
    """Return True when the ID holds a word from either list, however it is dressed up."""
    pieces = [piece for piece in SEPARATORS.split(user_id) if piece]
    joined = _disguises("".join(pieces))
    if any(_holds_word(joined, word) for word in anywhere):
        return True
    candidates = [joined, *(_disguises(piece) for piece in pieces)]
    return any(_is_word(forms, word) for forms in candidates for word in parts)
