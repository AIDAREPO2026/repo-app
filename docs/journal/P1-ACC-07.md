# P1-ACC-07 — Enforce the 5-device limit with the sixth-session policy

| Field | Value |
| --- | --- |
| Status | In review |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-07-device-limit` |
| Pull request | [#35](https://github.com/AIDAREPO2026/repo-app/pull/35) |
| Started | 2026-11-28 |
| Finished | Not finished |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-07--enforce-the-5-device-limit-with-the-sixth-session-policy)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Built the limit, the Signed-in devices page and the Sign-in rules screen. Checked in a browser, and checked that the parallel test fails without the row lock. Next: review. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | Sessions idle for 30 minutes are ended before counting | A closed browser never returns to be ended, so five of them would lock a Discom out for good | Pending review |
| 2026-11-28 | The limit is applied at the password and again after the second code. Half-signed-in sessions take no place | Nobody is asked for a code only to be refused, and the last place can go while they type | Pending review |
| 2026-11-28 | "Oldest" means the earliest sign-in, not the least recently used | The spec says oldest | Pending review |
| 2026-11-28 | A refusal is audited as the visitor (IP and device) acting on the login | A shared Member login has no session to name (SRS 2.3) | Pending review |
| 2026-11-28 | The refusal says "contact ITPED", but ITPED has no screen to sign out a Discom's devices. Forgot password signs all of them out | Not in the spec | Open |

## Blockers

None.
