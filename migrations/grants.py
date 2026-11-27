"""Grant table rights to the application role, the same way in every migration (data-model.md grants)."""

from alembic import op


def grant_to_app_role(table: str, rights: str, sequence: str | None = None) -> None:
    """Grant rights on a table, and USAGE on its sequence, to aida_app.

    Servers create the role. Locally it may not exist, so the grant is skipped there;
    the test setup creates it, so tests can check the grants.
    """
    sequence_grant = f"GRANT USAGE ON SEQUENCE {sequence} TO aida_app;" if sequence else ""
    # Table and right names come from migration code, never from user input.
    op.execute(f"""
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aida_app') THEN
        GRANT {rights} ON {table} TO aida_app;
        {sequence_grant}
    END IF;
END;
$$;
""")  # noqa: S608
