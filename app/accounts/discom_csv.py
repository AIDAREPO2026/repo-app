"""Read the Discom master list from a CSV file, row by row, for the import preview (FR-1.6, Q-09).

Checks each row on its own and against earlier rows. Checks against the saved list are
business rules and live in service.py.
"""

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import ValidationError

from app.accounts.schemas import DiscomForm

COLUMNS = ("name", "email_domain")
# The 70 Discoms fit easily; the limit stops a wrong file from filling the page.
MAX_ROWS = 500
FIELD_MESSAGES = {
    "name": "The name is missing or longer than 200 characters.",
    "email_domain": "The email domain is not a valid domain, such as discom.co.in.",
}


class DiscomCsvError(ValueError):
    """The file as a whole cannot be read, so no rows are shown."""


@dataclass
class ImportRow:
    """One data line of the file, with what will happen to it."""

    line: int
    name: str
    email_domain: str
    problem: str = ""
    already_listed: bool = False

    @property
    def will_be_added(self) -> bool:
        """Return True for a row that is new and has no problem."""
        return not self.problem and not self.already_listed


def read_discom_csv(text: str) -> list[ImportRow]:
    """Return one row per data line, each with its problem if it has one."""
    reader = csv.DictReader(io.StringIO(text.removeprefix("﻿")))
    _check_header(reader.fieldnames)
    rows: list[ImportRow] = []
    for record in reader:
        if len(rows) == MAX_ROWS:
            raise DiscomCsvError(f"The file has more than {MAX_ROWS} Discoms. Split it into smaller files.")
        rows.append(_read_row(reader.line_num, record))
    if not rows:
        raise DiscomCsvError("The file has no Discoms under its header line.")
    _mark_repeats(rows)
    return rows


def _check_header(fieldnames: Sequence[str] | None) -> None:
    """Refuse a file whose first line does not name both columns."""
    found = {name.strip().lower() for name in fieldnames or []}
    if not set(COLUMNS) <= found:
        raise DiscomCsvError("The first line must name the columns: name, email_domain.")


def _read_row(line: int, record: dict[str, str | None]) -> ImportRow:
    """Tidy and check one line, keeping what was typed so the preview can show it."""
    values = {key.strip().lower(): (value or "") for key, value in record.items() if key}
    raw = ImportRow(line=line, name=values["name"].strip(), email_domain=values["email_domain"].strip())
    try:
        form = DiscomForm(name=raw.name, email_domain=raw.email_domain)
    except ValidationError as error:
        raw.problem = FIELD_MESSAGES[str(error.errors()[0]["loc"][0])]
        return raw
    return ImportRow(line=line, name=form.name, email_domain=form.email_domain)


def _mark_repeats(rows: list[ImportRow]) -> None:
    """Mark a row whose name or domain already appeared earlier in the file."""
    first_line_for: dict[str, int] = {}
    for row in rows:
        if row.problem:
            continue
        for key in (f"name:{row.name.lower()}", f"domain:{row.email_domain}"):
            if key in first_line_for:
                row.problem = f"Same name or domain as line {first_line_for[key]}."
                break
        first_line_for.setdefault(f"name:{row.name.lower()}", row.line)
        first_line_for.setdefault(f"domain:{row.email_domain}", row.line)
