# Tests

`tests/<module>/test_<topic>.py` mirrors `app/`. Name tests after the requirement, for example `test_fr_13_3_teaser_hides_file_name`, or after the task code when there is no FR.

Tests run against a real PostgreSQL database and Redis, named by `TEST_DATABASE_URL` and `TEST_REDIS_URL` (see the root README). `tests/conftest.py` migrates it once per run, and the `db` fixture rolls back each test's changes.

- `e2e/`: Playwright scenarios run against staging
- `load/`: Locust load tests (`P4-PERF-01`)
