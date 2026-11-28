# P1-ACC-03 — Build Admin verification, activation and notification

| Field | Value |
| --- | --- |
| Status | In review |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-03-admin-verification` |
| Pull request | [#33](https://github.com/AIDAREPO2026/repo-app/pull/33) |
| Started | 2026-11-28 |
| Finished | Not finished |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-03--build-admin-verification-activation-and-notification)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Built the Registrations queue with Approve and Decline, email through the worker with retries, and migration 0010. Moved the four Admin list pages onto one renderer. Checked in a browser with a real worker. Next: review. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | The web app renders each email and queues the finished text; the worker only sends it | The worker needs no templates, and Hindi can follow the request later | Pending review |
| 2026-11-28 | A queued message, which can hold a sign-in code or set-password link, sits in Redis until it is sent. Task arguments are hidden from logs | Redis is internal and already holds registration state. For the security reviewer | Pending review |
| 2026-11-28 | A request for a deactivated Discom can only be declined | Approving it would give a login that cannot sign in | Pending review |
| 2026-11-28 | A declined applicant's User ID stays taken | User IDs are unique across every status (data-model) | Pending review |

## Blockers

None.
