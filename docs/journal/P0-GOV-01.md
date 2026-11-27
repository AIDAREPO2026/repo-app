# P0-GOV-01 — Record ITPED confirmation of decisions

| Field | Value |
| --- | --- |
| Status | Blocked |
| Owner | Raghvendra Singh |
| Branch | `docs/p0-gov-01-itped-decision-pack` |
| Pull request | Not opened |
| Started | 2026-11-27 |
| Finished | Not finished |

Spec: [docs/tasks/phase-0-mobilise.md](../tasks/phase-0-mobilise.md)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-27 | Raghvendra Singh | Wrote the [ITPED confirmation request](https://claude.ai/artifact/7mUgeXiPMsLjTYpBkAwRtC): D-01 to D-14 in plain words, each with what a change would affect and an Answer dropdown (Awaiting answer, Confirmed, Changed). It also lists the other overdue ITPED answers (Q-03, Q-04, Q-05, Q-09, Q-11) with their defaults. Next: the tech lead shares it with the ITPED Technical Lead. When answers come back, record each one in `docs/decisions.md` and update the affected specs. |
| 2026-11-27 | Raghvendra Singh | Started the task: preparing the confirmation pack for the ITPED Technical Lead. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-27 | The request goes to ITPED as a shared doc with an Answer dropdown per decision, rather than `docs/decisions.md` itself | ITPED can answer and comment row by row without reading the repository. `decisions.md` stays the source, and answers are copied back into it | Raghvendra Singh |
| 2026-11-27 | The request also lists Q-03, Q-04, Q-05, Q-09 and Q-11 | They are overdue ITPED answers that block staging, the schema and registration, so one request saves a second round | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| 2026-11-27 | Waiting for ITPED to confirm or change D-01 to D-14 (Q-01). The request is ready but has not been sent yet | Tech lead sends it; ITPED Technical Lead answers |
