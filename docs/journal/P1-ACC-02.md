# P1-ACC-02 — Build the registration form with CAPTCHA

| Field | Value |
| --- | --- |
| Status | Done |
| Owner | Raghvendra Singh |
| Branch | `feat/p1-acc-02-registration` |
| Pull request | [#19](https://github.com/AIDAREPO2026/repo-app/pull/19) |
| Started | 2026-11-28 |
| Finished | 2026-11-28 |

Spec: [docs/tasks/phase-1-platform-access.md](../tasks/phase-1-platform-access.md#p1-acc-02--build-the-registration-form-with-captcha)

## Log

Newest first. One line per working session: what was done, what is next.

| Date | Who | Entry |
| --- | --- | --- |
| 2026-11-28 | Raghvendra Singh | Reported by the user: the registration list still offered Discoms that already had a login or request. They are now left out. Branch `fix/p1-acc-02-hide-taken-discoms`. |
| 2026-11-28 | Raghvendra Singh | Merged #29 and #30 on the user's approval. Status Done; tracker row set to Done. |
| 2026-11-28 | Raghvendra Singh | Reserved IDs gained a category filter and a Removed tab with restore (#30). |
| 2026-11-28 | Raghvendra Singh | Reserved words now have categories; the screen is compact and shows more rows on scroll (#30). `data_table()` gained `compact` and `batch`, a `P1-UI-02` component. |
| 2026-11-28 | Raghvendra Singh | Added reserved User IDs with an Admin screen to manage them. Branch `feat/p1-acc-02-reserved-user-ids`, on top of #29. |
| 2026-11-28 | Raghvendra Singh | Reopened at the user's request: registration now verifies the email before the User ID is chosen, so only free User IDs are suggested. Replaces the browser-only suggestions of #28. Spec updated. Branch `feat/p1-acc-02-verify-email-first`. Opened #29; tracker row set to In review (rev 77). |
| 2026-11-28 | Raghvendra Singh | Approved by the user and merged as #19. In #20 (`P1-UI-02`) the registration and request-sent pages moved to the AIDA sign-in layout (`layouts/auth.html`) and the sign-in page kept the Register link; 355 unit and 21 e2e tests pass, including axe on `/register` in light and dark. Tracker row set to Done. |
| 2026-11-28 | Raghvendra Singh | Built the public `/register` form, the `/captcha/challenge` route, the vendored ALTCHA widget (3.7.0, external build) and the registration rules. Checked in the browser: the real widget solves our challenge under the CSP and a request creates a pending Member login. Unit tests (279), e2e and axe pass. Opened #19 and set the tracker row to In review. Next: review. |
| 2026-11-28 | Raghvendra Singh | Started the task. |

## Decisions and deviations

Anything decided while building that the spec does not say, and any change from the spec, with the reason. Write "None" if there are none.

| Date | Decision or deviation | Reason | Agreed by |
| --- | --- | --- | --- |
| 2026-11-28 | A Discom with a pending or active login is not listed on the public form. The server still refuses it if chosen | One login per Discom (FR-1.6). The form already said so after submitting; listing now shows at a glance which Discoms have a login, which the security review should accept or not | User; security review pending |
| 2026-11-28 | The reserved words are two settings in `app_setting`, edited on Reserved IDs; format rules are fixed in code. `portal` is reserved, so suggestions use `.office` | The user asked for a list Admin can change; changes are audited like other settings | User; security review pending |
| 2026-11-28 | A Discom's bracketed code, such as MSEDCL, is kept for that Discom. The server command that creates the first Admin is exempt from the rules | Stops one Discom posing as another; only a server operator can run the command | Pending tech lead review |
| 2026-11-28 | Registration takes three steps, and a taken User ID is now said on step 3 instead of being silently accepted | A suggestion must be free. Only someone who reads mail on the Discom's domain gets that far, with limited checks, so outsiders learn nothing | User; security review pending |
| 2026-11-28 | A request in progress lives in Redis (hashed token and code), not the database. No migration | It is not a login yet, and expiry cleans it up | Pending tech lead review |
| 2026-11-28 | A User ID or email already in use gets the same "sent" page as a good request, with nothing created and the reason in the audit event | The spec allows field errors only for format problems, so the form cannot be used to find existing User IDs. Cost: a Discom that picks a taken User ID gets no login and must contact ITPED, who can see the reason in the audit | Pending tech lead review |
| 2026-11-28 | A Discom that already has a pending or active login is told so on the form | Acceptance criterion; Discom names are already public in the list, so this reveals only that a request exists | Pending tech lead review |
| 2026-11-28 | The schema checks only lengths. Formats are checked by the service after the CAPTCHA, and shown next to each field | The spec wants the CAPTCHA checked before any other processing, and visitors need field errors, not a bare 422 | Pending tech lead review |
| 2026-11-28 | Only active Discoms are listed. Every request, accepted or not, is audited as `accounts.register`; refusals use result `denied` with a reason. The details hold the Discom ID and User ID, never the email or password | The audit table allows success, failure or denied. The email is personal data kept out of a 3-year log | Pending tech lead review |
| 2026-11-28 | Nginx limits `/register` and `/captcha/` to 10 requests a minute per address, burst 5 and 10 | Spec rate limit. The challenge route is included because each challenge costs the server a signature | Pending tech lead review |
| 2026-11-28 | Vendored only the widget's `dist/external` script, its CSS, the PBKDF2 worker and the licence. `static/js/captcha.js` registers the worker. The widget's logo and "Protected by ALTCHA" footer are hidden | The external build ships no worker, and inline scripts are blocked by CSP. axe failed the footer link (WCAG 1.4.1) and it points off-site; the MIT licence does not require it | Pending tech lead review |
| 2026-11-28 | Links inside a paragraph are now underlined everywhere (`p a` in `app.src.css`) | axe found the new "Sign in" link told apart by colour alone (WCAG 1.4.1); the same applies to the new link on the sign-in page | Pending tech lead review |
| 2026-11-28 | The design-system test now refuses inline `<script>` only, not every `<script>` | architecture.md allows self-hosted scripts and forbids inline ones; the widget needs one script file | Pending tech lead review |
| 2026-11-28 | The privacy notice is draft text, marked as such on the page | The final text is ITPED's (Q-10) | Pending tech lead review |

## Blockers

What stops the task, who can unblock it, and since when. Write "None" if there are none.

| Since | Blocker | Who can unblock it |
| --- | --- | --- |
| | None | |
