"""Check a running site's security headers and hidden paths, for local use and CI.

The expected headers are read from the table in docs/security.md, so the doc
stays the single source. Also checks that internal paths return 404 from outside.

    uv run python scripts/check_headers.py https://localhost --insecure

--insecure skips certificate checks, for the self-signed local certificate only.
"""

import re
import sys
from pathlib import Path

import httpx

SECURITY_DOC = Path(__file__).resolve().parent.parent / "docs" / "security.md"
HEADER_ROW = re.compile(r"^\| `([A-Za-z-]+)` \| `(.+)` \|$")

# Paths Nginx must hide: the app's internal endpoints (tusd hooks) and the protected-file location.
HIDDEN_PATHS = ["/internal/tusd-hooks", "/_protected/files/anything"]


def expected_headers() -> dict[str, str]:
    """Return the header table from docs/security.md as name to value."""
    headers: dict[str, str] = {}
    for line in SECURITY_DOC.read_text().splitlines():
        row = HEADER_ROW.match(line)
        if row:
            headers[row.group(1)] = row.group(2)
    if not headers:
        raise SystemExit("No header table found in docs/security.md")
    return headers


def header_problems(response: httpx.Response) -> list[str]:
    """Return one line for each expected header that is missing or different."""
    problems = []
    for name, value in expected_headers().items():
        actual = response.headers.get(name)
        if actual != value:
            problems.append(f"{name}: expected {value!r}, got {actual!r}")
    return problems


def hidden_path_problems(client: httpx.Client, base_url: str) -> list[str]:
    """Return one line for each internal path that does not return 404."""
    problems = []
    for path in HIDDEN_PATHS:
        status = client.get(base_url + path).status_code
        if status != 404:
            problems.append(f"{path}: expected 404, got {status}")
    return problems


def main() -> int:
    """Run every check against the URL given on the command line."""
    arguments = [argument for argument in sys.argv[1:] if not argument.startswith("--")]
    if len(arguments) != 1:
        raise SystemExit(__doc__)
    base_url = arguments[0].rstrip("/")
    with httpx.Client(verify="--insecure" not in sys.argv, timeout=10) as client:
        response = client.get(base_url + "/healthz")
        problems = header_problems(response) + hidden_path_problems(client, base_url)
    for problem in problems:
        print(problem)
    if problems:
        return 1
    print(f"{base_url}: all security headers present, internal paths hidden")
    return 0


if __name__ == "__main__":
    sys.exit(main())
