"""Server-only account commands (P1-ACC-09, P1-ACC-10).

    python -m app.accounts.cli create-admin --user-id itped.admin --full-name "A Person" --email a@itped.in
    python -m app.accounts.cli reset-mfa --user-id itped.admin

create-admin makes an Admin with a password typed at the prompt, for the first Admin or to
recover when no Admin can sign in. reset-mfa removes a login's second factor, for when the
only Admin has lost their phone. Both need the server's database settings, so they only run there.
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from app.accounts.schemas import PrivilegedAccountForm
from app.accounts.service import AccountRuleError, create_first_admin, reset_mfa_on_server
from app.core.config import load_config
from app.core.db import make_session_factory


def main(argv: list[str] | None = None) -> int:
    """Run a command and return the exit code."""
    args = _parser().parse_args(argv)
    if args.command == "reset-mfa":
        return reset_mfa(args.user_id)
    return create_admin(args)


def create_admin(args: argparse.Namespace) -> int:
    """Create an Admin with a password typed at the prompt."""
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


def reset_mfa(user_id: str) -> int:
    """Remove a login's second factor and end its sessions, so it enrols again at its next sign-in."""
    with make_session_factory(load_config().database_url)() as db:
        try:
            login = reset_mfa_on_server(db, user_id)
        except AccountRuleError as error:
            print(error, file=sys.stderr)
            return 1
        db.commit()
    print(f"Reset two-step sign-in for {login.user_id}. They set it up again at their next sign-in.")
    return 0


def _parser() -> argparse.ArgumentParser:
    """Describe the commands and their options."""
    parser = argparse.ArgumentParser(prog="python -m app.accounts.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Create an Admin with a password")
    create.add_argument("--user-id", required=True)
    create.add_argument("--full-name", required=True)
    create.add_argument("--email", required=True)
    reset = commands.add_parser("reset-mfa", help="Remove a login's second factor")
    reset.add_argument("--user-id", required=True)
    return parser


if __name__ == "__main__":
    sys.exit(main())
