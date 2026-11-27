"""Server-only account commands (P1-ACC-09).

    python -m app.accounts.cli create-admin --user-id itped.admin --full-name "A Person" --email a@itped.in

Creates an Admin with a password typed at the prompt, for the first Admin or to recover
when no Admin can sign in. It needs the server's database settings, so it only runs there.
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from app.accounts.schemas import PrivilegedAccountForm
from app.accounts.service import AccountRuleError, create_first_admin
from app.core.config import load_config
from app.core.db import make_session_factory


def main(argv: list[str] | None = None) -> int:
    """Run a command and return the exit code."""
    args = _parser().parse_args(argv)
    try:
        form = PrivilegedAccountForm(
            login_type="admin", full_name=args.full_name, email=args.email, user_id=args.user_id
        )
    except ValidationError as error:
        fields = ", ".join(str(issue["loc"][0]) for issue in error.errors())
        print(f"Check these values: {fields}.", file=sys.stderr)
        return 1
    password = getpass.getpass("Password: ")
    if getpass.getpass("Type it again: ") != password:
        print("The two passwords do not match.", file=sys.stderr)
        return 1
    with make_session_factory(load_config().database_url)() as db:
        try:
            login = create_first_admin(db, form, password)
        except AccountRuleError as error:
            print(error, file=sys.stderr)
            return 1
        db.commit()
    print(f"Created Admin {login.user_id}. They can sign in now.")
    return 0


def _parser() -> argparse.ArgumentParser:
    """Describe the commands and their options."""
    parser = argparse.ArgumentParser(prog="python -m app.accounts.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Create an Admin with a password")
    create.add_argument("--user-id", required=True)
    create.add_argument("--full-name", required=True)
    create.add_argument("--email", required=True)
    return parser


if __name__ == "__main__":
    sys.exit(main())
