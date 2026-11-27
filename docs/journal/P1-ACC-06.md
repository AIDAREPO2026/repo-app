# P1-ACC-06 — Build server-side sessions, CSRF protection and idle timeout

| Field | Value |
| --- | --- |
| Status | In review |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-06-sessions-csrf` |
| Pull request | Not opened |
| Started | 2026-11-28 |
| Finished | Not finished |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-06--build-server-side-sessions-csrf-protection-and-idle-timeout)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Built `user_session` (migration 0006) and `app/core/sessions.py`: session loading, the idle end, rotation at sign-in, cookies and CSRF. Added the sign-in and sign-out routes and pages, and a Sign out button in the layout. 16 new tests; 126 unit and 6 e2e tests pass, and Ruff, mypy and `alembic check` are clean. Checked by hand in the browser: a visitor is redirected, a wrong password gets the generic message, a right one opens the requested page, and after sign-out the dashboard redirects again, with no console errors. Next: pull request. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | Sessions and CSRF are app-wide FastAPI dependencies (`load_session`, `check_csrf`) in `app/core/sessions.py`, not middleware as the spec says | Middleware is async, so the synchronous database calls would block the event loop. As dependencies they stay plain, appear in the route registry, and set `request.state` for `current_login` | Raghvendra Singh |
| 2026-11-28 | `check_csrf` is `async def` | Reading a submitted form is async in Starlette. It makes no database calls, and the form is cached for the route | Raghvendra Singh |
| 2026-11-28 | Visitor forms, such as sign-in, are protected too: the token is an HMAC of a `drr_csrf` cookie, keyed with `SECRET_KEY` | The spec checks every POST, and visitors have no session. Signing stops a cookie planted from another subdomain (the SCORM player, Phase 5) from being enough | Raghvendra Singh |
| 2026-11-28 | Failed sign-ins go to `login_attempt` only. Sign-in, sign-out and session ends go to the audit | `login_attempt` is the failure log from `P1-ACC-04`. The audit records what a signed-in session did | Raghvendra Singh |
| 2026-11-28 | `sign_in`, `sign_out` and `after_sign_in_path` are in `app/accounts/service.py`. `next` is followed only when it is a path on this site | Routes stay thin, and the sign-in page cannot be used to send people to another site | Raghvendra Singh |
| 2026-11-28 | The server accepts the `X-CSRF-Token` header. The layout will send it with `hx-headers` when HTMX is added | HTMX is not vendored yet ("use only if needed") | Raghvendra Singh |
| 2026-11-28 | After a failed sign-in, the User ID is filled in again. The password never is | So people do not have to retype it | Raghvendra Singh |
| 2026-11-28 | `mfa_pending` exists but is always false | MFA is `P1-ACC-10` | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| None | | |
