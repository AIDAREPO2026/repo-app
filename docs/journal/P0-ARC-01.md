# P0-ARC-01 — Design the database schema

| Field | Value |
| --- | --- |
| Status | In review |
| Owner | Raghvendra Singh |
| Branch | `docs/p0-arc-01-data-model` |
| Pull request | Not opened |
| Started | 2026-11-27 |
| Finished | Not finished |

Spec: [docs/tasks/phase-0-mobilise.md](../tasks/phase-0-mobilise.md#p0-arc-01--design-the-database-schema)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-27 | Raghvendra Singh | Wrote `docs/data-model.md`, linked it from `architecture.md` and the docs index. Opened the pull request and set the tracker row to In review. Next: a second developer reviews it. |
| 2026-11-27 | Raghvendra Singh | Started the task, before `P0-GOV-01` is Done. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-27 | Added a `login_token` table for set-password, reset, email MFA codes and the extra-address confirmation | One place for hashing, expiry and single use, instead of four copies. Created by `P1-ACC-05`, added to `architecture.md` | Raghvendra Singh |
| 2026-11-27 | Added `declined` to `login.status`, and updated the `P1-ACC-08` spec | A declined registration must free the Discom's one-Member-login slot so it can register again, without pretending it was ever active | Raghvendra Singh |
| 2026-11-27 | One `content_file` table for item files, Gallery files and workspace documents, with exactly one parent set | Upload, scanning and delivery are written once. Workspace files never join to content queries, so no visibility rule can leak them | Raghvendra Singh |
| 2026-11-27 | A substantive edit's review state is `content_item.working_state`, while `state` stays `published` | The published version stays live (D-09) and the item's own state stays truthful | Raghvendra Singh |
| 2026-11-27 | Retired is a flag (`retired`), not a value of `state`, following D-08 and `P5-LIFE-02`. `workflow.md` still lists Retired as a state | `workflow.md` should be aligned by `P5-LIFE-02`, or in the `P0-GOV-01` follow-up if ITPED changes D-08 | Raghvendra Singh |
| 2026-11-27 | Endorsement criteria and Gallery entry conditions are settings (JSON in `app_setting`), not tables | They are small Admin-edited lists, which is what settings are for | Raghvendra Singh |
| 2026-11-27 | Started before its dependency `P0-GOV-01` is Done, designing on the proposed decisions D-01 to D-14 | ITPED's answers are slow to arrive and every Phase 1 data task waits on this design. Any changed answer is applied to `data-model.md` in the `P0-GOV-01` follow-up | Raghvendra Singh |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
