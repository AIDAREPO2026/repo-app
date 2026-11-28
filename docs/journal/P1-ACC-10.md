# P1-ACC-10 — Add MFA by authenticator app and email code

| Field | Value |
| --- | --- |
| Status | In progress |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-10-mfa` |
| Pull request | Not opened |
| Started | 2026-11-28 |
| Finished | Not finished |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-10--add-mfa-by-authenticator-app-and-email-code)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Built MFA: migration 0008 (MFA columns on `login`, the `locked` session end reason), `app/accounts/mfa.py` (Fernet, TOTP, QR code), email codes in `app.accounts.tokens`, the code page with enrolment, the Security page, Member on and off, and Admin reset in the Accounts drawer. `FERNET_KEY` is now checked at startup. 17 new tests; 219 unit tests and 14 e2e tests pass, and Ruff, mypy, `alembic check`, the 0008 downgrade and `pip-audit` are clean. Checked by hand in the browser: enrolment with an app, a wrong code refused, the right code accepted, and the Security page. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | A session waiting for its second factor puts its login on `request.state.mfa_login`, not `request.state.login`, so every guard treats it as signed out and sends it to `/mfa`. The MFA routes are marked `public_route` and take the login from `mfa_pending_login` | No route can let a half-signed-in session through by mistake, including routes added later | Pending tech lead review |
| 2026-11-28 | Wrong codes count towards the password lockout (5 in a row, 15 minutes), logged in `login_attempt` with reason `mfa_failed` and audited as `accounts.mfa`. At the lockout the session ends with the new end reason `locked` | This is the rate limit the spec asks for, using the rule that already exists instead of a second one | Pending tech lead review |
| 2026-11-28 | Added `login.mfa_totp_last_step`, which data-model.md did not plan | Without it an authenticator code could be used again within its 30 to 90 seconds, which the "reused code is refused" criterion forbids | Pending tech lead review |
| 2026-11-28 | An email code's stored hash covers the login and its issue time as well as the code | Six-digit codes repeat, and `login_token.token_hash` is unique | Pending tech lead review |
| 2026-11-28 | A Member turns MFA on from a new Security page: their session goes back to the code page to choose and confirm a method. Turning it off asks for no code | Reuses the enrolment flow. ponytail: a stolen Member session could turn MFA off; ask for a current code if review wants it | Pending tech lead review |
| 2026-11-28 | Admin reset ends the person's sessions. The reset button is only on the privileged Accounts screen for now | They enrol again at their next sign-in. Member account screens come in a later task, and `reset_mfa()` already works for Members | Pending tech lead review |
| 2026-11-28 | `FERNET_KEY` is checked when the app starts, and the test environment has a real Fernet key | A placeholder key would otherwise fail only at someone's first enrolment | Pending tech lead review |
| 2026-11-28 | The e2e Admin signs in once per run, with the new `E2E_ADMIN_TOTP_SECRET` for its authenticator code | Codes are single use, so signing in again within 30 seconds would be refused | Pending tech lead review |
| 2026-11-28 | The `P1-ACC-06` session tests now sign in as a Member | Those tests check sessions, not MFA; an Admin now stops at the code page, which `test_mfa.py` covers | Pending tech lead review |
| 2026-11-28 | Follow-ups: no limit on "Send a new code" beyond Nginx rate limits, and no command-line reset when the only Admin loses their phone (`create-admin` can add a second Admin who resets it) | Kept the task to its scope | Pending tech lead review |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| None | | |
