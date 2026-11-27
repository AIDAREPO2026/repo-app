# P1-ACC-04 — Add password policy, lockout and failed-attempt logging

| Field | Value |
| --- | --- |
| Status | In review |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-04-password-lockout` |
| Pull request | Not opened |
| Started | 2026-11-28 |
| Finished | Not finished |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-04--add-password-policy-lockout-and-failed-attempt-logging)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Built `app/accounts/passwords.py`, the lockout fields and `login_attempt` (migration 0005), and the service functions with `authenticate()`. 17 new tests. Removing the row lock makes the parallel test fail 3 runs out of 3; with the lock it passes. 109 tests pass, and Ruff, mypy and `alembic check` are clean. Next: pull request. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | Added `authenticate(db, user_id, password, ip, user_agent)`, which composes the lookup, lockout, status check and password check | The acceptance criterion "the correct password is refused during the lockout" needs them together. `P1-ACC-06` builds the sign-in page on it | Raghvendra Singh |
| 2026-11-28 | `record_failed_attempt` takes the login, and unknown User IDs are logged inside `authenticate()` | Only a known login has a counter to raise. Unknown IDs are still stored, with `login_id` null | Raghvendra Singh |
| 2026-11-28 | An unknown User ID, or a login without a password, is still checked against a fixed hash | The response takes as long as a wrong password, so timing does not reveal which accounts exist | Raghvendra Singh |
| 2026-11-28 | The counter resets when the lockout starts, and attempts during a lockout are logged as `locked` without counting | After 15 minutes the next 5 failures lock it again, and an attacker cannot extend the lockout indefinitely | Raghvendra Singh |
| 2026-11-28 | Pending, declined and deactivated logins are refused before the password check, logged as `inactive` | The caller shows the same message, so nothing is revealed. Such logins do not count towards a lockout | Raghvendra Singh |
| 2026-11-28 | `verify_password` returns the hash to keep (rehashed if the parameters changed), or None | The caller saves one value, instead of handling a match flag and a separate rehash step | Raghvendra Singh |
| 2026-11-28 | Risk R-08 stands: anyone who knows a Discom's User ID can lock it for 15 minutes | As in `plan.md`. CAPTCHA on sign-in after repeated failures is the possible later mitigation | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| None | | |
