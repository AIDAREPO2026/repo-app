# P1-ACC-01 — Build the Discom master list and Admin screen

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-01-discom-list` |
| Pull request | [#18](https://github.com/AIDAREPO2026/repo-app/pull/18) |
| Started | 2026-11-28 |
| Finished | 2026-11-28 |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-01--build-the-discom-master-list-and-admin-screen)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Add Discom now warns that suggested names are not verified and refuses until the Admin confirms the details were checked (#27). |
| 2026-11-28 | Raghvendra Singh | The Add Discom name field now suggests utility names as you type. Branch `feat/p1-acc-01-discom-name-suggestions`. |
| 2026-11-28 | Raghvendra Singh | With `P1-UI-02`: deactivating a Discom now reports as a warning (amber) rather than a success. No change to behaviour. (#25) |
| 2026-11-28 | Raghvendra Singh | Security follow-up, found while researching Discom domains: public mail services such as gmail.com could be listed. They are now refused on add, edit and import, and at registration. Branch `fix/p1-acc-01-free-email-domains`. |
| 2026-11-28 | Raghvendra Singh | Merged #18 on the user's approval and set the tracker row to Done. |
| 2026-11-28 | Raghvendra Singh | Built the `organisation` table (migration 0009), the Admin Discoms screen (list, add, edit, deactivate, reactivate), the CSV import with a preview, the `seed-test-discoms` command and the inactive-Discom sign-in rule. Checked locally in the browser; unit and e2e tests pass. Opened #18 and set the tracker row to In review. Next: review. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | Adding a Discom needs a ticked confirmation, checked on the server. Editing and CSV import do not ask; import already has a preview step | Asked for by the user. The domain decides who may register (D-11) | User |
| 2026-11-28 | Name suggestions are a draft list from public sources, in code, using the browser's `datalist`. No email domain is filled in | ITPED has not supplied the list (Q-09), and a wrong domain would let an outsider register. Replace with ITPED's list when it arrives | User; pending tech lead review |
| 2026-11-28 | A fixed list of public mail domains (`PUBLIC_EMAIL_DOMAINS`) cannot be used for a Discom, and registration refuses them even if one is already listed. Broad government domains such as `nic.in` are not blocked; that is part of D-11 for ITPED | Anyone could get an address and ask for that Discom's login. Several Discoms publish only Gmail addresses, so ITPED needs another way to identify them | User; list pending tech lead and security review |
| 2026-11-28 | Added Reactivate next to Deactivate | Deactivating a Discom by mistake would otherwise need a database fix. Nothing is deleted (SRS 6.3) | Pending tech lead review |
| 2026-11-28 | Deactivating a Discom ends the open sessions of its Member login, and sign-in refuses it with the usual message, logged with reason `inactive` | The spec says its Member login cannot sign in; ending sessions makes that apply at once, as for a deactivated account | Pending tech lead review |
| 2026-11-28 | The CSV import preview keeps nothing on the server: the file text goes back in a hidden field and is checked again when saved. Rows with a problem, repeats and Discoms already listed are skipped and shown; the rest are added. Limits: 100 KB and 500 rows, UTF-8, columns `name` and `email_domain` | No temporary table or file to clean up; checking again on save means the preview cannot be tampered with | Pending tech lead review |
| 2026-11-28 | Names are unique ignoring case (index on `lower(name)`); domains are stored lowercase with any leading `@` removed | "North Discom" and "north discom" are the same Discom; Admins paste domains in many forms | Pending tech lead review |
| 2026-11-28 | Migration 0009 gives any Member login that already has an `organisation_id` an inactive placeholder Discom before adding the foreign key | Earlier test data used random IDs; the key could not be added otherwise. Placeholders are inactive, so those logins cannot sign in until an Admin fixes them | Pending tech lead review |
| 2026-11-28 | Test Discoms are seeded by a `seed-test-discoms` CLI command that refuses outside local, development, test and staging. The same list is used by the test data | Seeding in production must be impossible, and one list avoids copies | Pending tech lead review |
| 2026-11-28 | The edit route is `POST /admin/discoms/{id}/edit`, and the Accounts and Discoms screens share one `run_admin_change` helper in the router | `/admin/discoms/import` would otherwise match `/{id}`; the helper avoids copying the change-and-redirect code | Pending tech lead review |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| | None | |
