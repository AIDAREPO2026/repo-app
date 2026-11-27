# P0-SET-02 — Add configuration, database connection and Alembic baseline

| Field | Value |
| --- | --- |
| Status | In review |
| Owner | Raghvendra Singh |
| Branch | `feat/p0-set-02-config-db-alembic` |
| Pull request | [AIDAREPO2026/repo-app#2](https://github.com/AIDAREPO2026/repo-app/pull/2) |
| Started | 2026-11-27 |
| Finished | Not finished |

Spec: [docs/tasks/phase-0-mobilise.md](../tasks/phase-0-mobilise.md)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-27 | Raghvendra Singh | Opened [the pull request](https://github.com/AIDAREPO2026/repo-app/pull/2) and set status to In review. Next: review and approval. |
| 2026-11-27 | Raghvendra Singh | Built config, database session, constants, time helpers, the settings store and JSON logging, with Alembic migrations `0001` (empty baseline) and `0002` (`app_setting`). All acceptance criteria pass against PostgreSQL 19.0. Next: review. |
| 2026-11-27 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-27 | Routes get a session through `DbSession`, which uses `Depends(get_db, scope="function")` | FastAPI's default runs the commit after the response is sent, so a failed commit would show the user a success | Raghvendra Singh |
| 2026-11-27 | `set_setting` takes `actor` as a login id for now, and writes no audit event yet | The login table (`P1-ACC-08`) and `record()` (`P1-AUD-01`) do not exist; both are wired when they land | Raghvendra Singh |
| 2026-11-27 | Integer settings have a minimum of 1; only `limit_image_mb` has a maximum (20, D-01). `digest_frequency` allows `daily` or `weekly` | The SRS sets no other upper bounds; the digest choices are confirmed in Phase 5 | Raghvendra Singh |
| 2026-11-27 | IST is a fixed +05:30 offset, not a time-zone database lookup | India has no daylight saving, and slim Docker images may lack tz data | Raghvendra Singh |
| 2026-11-27 | Logging lives in `app/core/log_setup.py`; text after `Authorization`, `Cookie` or `Set-Cookie` is removed to the end of the line | A module named `logging.py` is easily confused with the standard library; cookie values contain spaces and `;` | Raghvendra Singh |
| 2026-11-27 | Tests use a separate `aida_test` database (`TEST_DATABASE_URL`, default port 5434), and two extra shared helpers are listed in the conventions table | The migration test drops every table, so it must never touch a developer's data | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

None.
