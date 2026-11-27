# P1-AUD-01 — Build the append-only audit table and record function

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-aud-01-audit-trail` |
| Pull request | #11 |
| Started | 2026-11-27 |
| Finished | 2026-11-28 |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-aud-01--build-the-append-only-audit-table-and-record-function)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Approved by the tech lead and merged. Tracker row set to Done. |
| 2026-11-28 | Raghvendra Singh | Built `audit_event` (migration 0003) with checks, indexes, the append-only trigger and the `aida_app` grant. Added `app.audit.service.record()` and `Actor`, and wired `set_setting`. 10 new tests; full suite, Ruff, mypy and `alembic check` pass. Opened #11 with the `security` label (created, it did not exist yet) and set the tracker row to In review. |
| 2026-11-27 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | `record()` takes an `Actor` (kind, login ID, session ID, IP, user agent), defined in `app.audit.service`, with a `SYSTEM` actor for jobs and setup | One value carries everything the audit needs. `P1-ACC-06` and `P1-ACC-08` build it from the session | Raghvendra Singh |
| 2026-11-28 | `record()` refuses a Member actor without a session ID and IP | Enforces SRS 2.3 at the one place every audit goes through, instead of trusting each caller | Raghvendra Singh |
| 2026-11-28 | The trigger also blocks TRUNCATE | TRUNCATE skips row triggers, so without it the trail could still be wiped | Raghvendra Singh |
| 2026-11-28 | `app_setting.updated_by` changed from integer to `uuid` in this task, not `P1-ACC-08` | `set_setting` now takes an `Actor`, whose login ID is a UUID. The foreign key still comes with the `login` table | Raghvendra Singh |
| 2026-11-28 | The grant runs only when the `aida_app` role exists, and the test setup creates that role | Servers create the role (data-model.md); local Docker has a single user. Tests still prove the grant | Raghvendra Singh |
| 2026-11-28 | `actor_login_id` has no foreign key yet | The `login` table arrives in `P1-ACC-08`, which adds the key | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| None | | |
