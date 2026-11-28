# P1-ACC-05 — Build password reset with CAPTCHA

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-05-password-reset` |
| Pull request | [#34](https://github.com/AIDAREPO2026/repo-app/pull/34) |
| Started | 2026-11-28 |
| Finished | 2026-11-28 |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-05--build-password-reset-with-captcha)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Merged #34 on the user's approval. Status Done; tracker row set to Done. No second review or staging check is recorded. |
| 2026-11-28 | Raghvendra Singh | At the user's request, a reset now emails the owner that the password changed (#34). The user also confirmed the two open choices. |
| 2026-11-28 | Raghvendra Singh | Built the forgot-password and reset pages. Closed two leaks found on the way: links built from the Host header, and tokens in access logs. Checked the whole journey in a browser with a real worker. Next: review. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | Every active login can reset, privileged ones included. Two-step sign-in is untouched | The spec says "the account"; the second factor still protects privileged logins | User; security review pending |
| 2026-11-28 | One link per account in 5 minutes, and a newer link retires the older. Per address, Nginx limits requests like registration | Spec asks for both limits without figures | User; security review pending |
| 2026-11-28 | New setting `PORTAL_URL`; staging and production will not start without an https value | A link built from the Host header would let a stranger point a victim's reset link at their own site. This also changes set-password and approval emails | Security review pending |
| 2026-11-28 | Link tokens are removed from app logs and the Nginx access log is off for those addresses | security.md: never log tokens. Set-password links were being logged | Security review pending |
| 2026-11-28 | A reset is audited as the visitor (IP and device) acting on the account | A shared Member login cannot be named as actor without a session (SRS 2.3) | Security review pending |
| 2026-11-28 | A reset emails the owner, added to the spec's scope. The email has no link. A first password set from a new-account link sends nothing | A change the owner did not make should be noticed; a first password is not a change | User |

## Blockers

None.
