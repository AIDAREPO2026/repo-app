# Tests

`tests/<module>/test_<topic>.py` mirrors `app/`. Name tests after the requirement, for example `test_fr_13_3_teaser_hides_file_name`, or after the task code when there is no FR.

Tests run against a real PostgreSQL database and Redis, named by `TEST_DATABASE_URL` and `TEST_REDIS_URL` (see the root README). `tests/conftest.py` migrates it once per run, and the `db` fixture rolls back each test's changes.

- `e2e/`: Playwright scenarios. They run only when `E2E_BASE_URL` names a running portal, so a plain `pytest` skips them. Tests that need the Admin also need `E2E_ADMIN_USER_ID`, `E2E_ADMIN_PASSWORD` and `E2E_ADMIN_TOTP_SECRET`, the authenticator secret of that Admin (P1-ACC-10), and skip without them. `e2e/axe.py` checks a page for WCAG 2.1 AA issues
- `files/`: sample files for upload tests (see [files/README.md](files/README.md))
- `fixture_data.py`: fictional Discoms and one login of each type. Passwords come from environment variables, never the repository
- `load/`: Locust load tests (`P4-PERF-01`)
