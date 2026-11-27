# P1-ACC-08 — Add the four login types and role guards

| Field | Value |
| --- | --- |
| Status | In review |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-08-login-types-guards` |
| Pull request | #12 |
| Started | 2026-11-28 |
| Finished | Not finished |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-08--add-the-four-login-types-and-role-guards)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Built the `login` table (migration 0004), with its checks and the one-Member-login-per-Discom index. Added foreign keys from `audit_event` and `app_setting`, and `app/accounts/guards.py` (`require_login_type`, `public_route`, `current_login`, `actor_for`). The dashboards are now four guarded routes, and OpenAPI is off. Added the route registry and refusal tests. 92 unit and 5 e2e tests pass (4 e2e skipped), and Ruff, mypy and `alembic check` are clean. Opened #12 with the `security` label, and set the tracker row to In review. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | `current_login()` reads `request.state.login` and returns None until the session middleware exists (`P1-ACC-06`). Tests override it | Sessions depend on this task, so this task cannot sign anyone in. Every protected route already sends visitors to `/login`, which `P1-ACC-06` builds | Raghvendra Singh |
| 2026-11-28 | The guard is a small class, `LoginTypeGuard`, returned by `require_login_type()` | The route registry test finds guards with `isinstance`, with no attributes on functions | Raghvendra Singh |
| 2026-11-28 | A refusal is audited in its own transaction | The route's session rolls back when the guard raises, which would lose the audit row | Raghvendra Singh |
| 2026-11-28 | The registry test walks `fastapi.routing.iter_route_contexts()` | FastAPI 0.165 keeps included routers as `_IncludedRouter` entries, so `app.routes` alone hides them | Raghvendra Singh |
| 2026-11-28 | Turned off `/openapi.json` (`openapi_url=None`) | It published every route, including protected ones, to anyone, outside the guards. `/api/v1` can turn it back on behind a guard | Raghvendra Singh |
| 2026-11-28 | The dashboard shell is four routes, one per login type, instead of `/dashboard/{login_type}` | Each route declares exactly one allowed type, so the refusal test covers every wrong type | Raghvendra Singh |
| 2026-11-28 | `organisation_id` has no foreign key yet. The Approver and Reviewer uniqueness indexes are left to `P1-ACC-09` | The `organisation` table arrives in `P1-ACC-01`. The one-Approver and one-primary-Reviewer rules belong to `P1-ACC-09` | Raghvendra Singh |
| 2026-11-28 | `migrations/grants.py` holds the grant helper, now used by 0003 and 0004 | One copy of the conditional grant, instead of one per migration | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| None | | |
