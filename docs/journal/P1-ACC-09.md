# P1-ACC-09 — Build privileged account management

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-09-privileged-accounts` |
| Pull request | #15 |
| Started | 2026-11-28 |
| Finished | 2026-11-28 |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-09--build-privileged-account-management)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Merged and closed #15; the tracker row now says Done. |
| 2026-11-28 | Raghvendra Singh | Merged main (P1-UI-02) and rebuilt the Accounts and set-password screens with the design system. The Accounts page has a page header, an Add account modal, an accounts table in a card, and a Manage drawer for each account with a confirmation modal before deactivating. Added breadcrumbs. The field macro gained `id`, `pattern` and `maxlength` so several forms can share one page. 185 unit tests and 12 e2e tests pass. Checked by hand in the browser. |
| 2026-11-28 | Raghvendra Singh | Opened #15 with the `security` label, and set the tracker row to In review. |
| 2026-11-28 | Raghvendra Singh | Built `login_token` and the account rules (migration 0007), `app/accounts/tokens.py`, `app/core/email.py`, the Accounts screen (create, deactivate, reassign, primary or alternate Reviewer, send a new link), the set-password page and `python -m app.accounts.cli create-admin`. Moved shared sign-in and CSRF test helpers into `tests/accounts/conftest.py`. 13 new tests; 166 unit tests pass, and Ruff, mypy, `alembic check` and `pip-audit` are clean. Checked by hand in the browser against a local SMTP catcher: create an Approver, a second Approver refused, the email and link, weak password refused, link refused on reuse, and deactivation. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | `login_token` is created here, not in `P1-ACC-05` as data-model.md planned | This task is the first to need it, for set-password links. `P1-ACC-05` reuses `app.accounts.tokens` | Pending tech lead review |
| 2026-11-28 | `app.core.email.send_email(to, subject, template, context)` is created here and sends at once through `smtplib`, with new optional `SMTP_*` and `MAIL_FROM` settings | The spec needs the link emailed and `P1-ACC-03` is not started. The signature matches the `P1-ACC-03` spec, so that task only moves sending to Celery with retries | Pending tech lead review |
| 2026-11-28 | The create form also asks for a User ID | The spec lists full name and email, but every login needs a User ID to sign in, in the fixed format | Pending tech lead review |
| 2026-11-28 | Added a "Send a new link" action for accounts that have not set a password | Without it an expired link would leave the account unusable, as the email already says to ask an Admin | Pending tech lead review |
| 2026-11-28 | The Reviewer rule is a deferred exclusion constraint, not the planned unique index. The planned `UNIQUE (lower(email))` index on current logins is added now, for FR-2.7 | Only a constraint can be deferred, which swapping primary and alternate needs. The email index stops two current accounts sharing an email | Pending tech lead review |
| 2026-11-28 | New accounts are active with no password, and cannot sign in until it is set | Keeps "one active Approver" true from creation, so a second one cannot be created while the first sets a password | Pending tech lead review |
| 2026-11-28 | `create-admin` asks for the password at the prompt instead of emailing a link | It is run by the first Admin on the server, which may not have mail or know the site address yet. It also recovers when no Admin can sign in | Pending tech lead review |
| 2026-11-28 | Each account's actions sit in one Manage drawer, not as buttons in the table row | Four buttons in a row overflowed the table on laptop screens. A drawer keeps the table easy to scan | Pending tech lead review |
| 2026-11-28 | Reassign moves no assignments yet | Items and `content_item.reviewer_login_id` arrive in Phase 2. Follow-up: `P2-WF-02` should move open assignments in `reassign_account()` | Pending tech lead review |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| None | | |
