# Phase 1: Platform and access

**Dates:** 26 to 30 November 2026 · **Tasks:** 17 · **Points:** 39 (Dev 31, QA 8)

**Goal:** Discoms can register and be activated, all four login types work securely, and every action is audited.

**Build order:** `P1-AUD-01` and `P1-UI-01` first. Then `P1-ACC-08` → `P1-ACC-04` → `P1-ACC-06`, with `P1-UI-02` alongside once `P1-ACC-08` lands. Then the rest of the ACC tasks in parallel. `P1-SEC-01` comes last.

**Exit criteria**

- [ ] A Discom registers and Admin activates it
- [ ] A sixth Member session follows the Admin policy
- [ ] Every privileged login requires MFA
- [ ] Every login and administrative action appears in the audit log
- [ ] The design-system style guide is reviewed, and Phase 1 pages use only its components

---

### P1-AUD-01 — Build the append-only audit table and record function

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P0-SET-02`, `P0-ARC-01` | FR-4.6, FR-12.1, SRS 2.3 accountability note, [security.md](../security.md) |

**Goal:** one tamper-resistant audit trail that every feature writes to the same way.

**Scope**

- An `audit_event` table with: `id` (bigint), `occurred_at`, `actor_login_id` (nullable), `actor_kind` (`member`, `admin`, `reviewer`, `approver`, `anonymous` or `system`), `session_id`, `ip`, `user_agent`, `action`, `target_type`, `target_id`, `result` (`success`, `failure` or `denied`) and `details` (jsonb).
- A database trigger that raises an error on UPDATE or DELETE of `audit_event`.
- A grant so the application role has INSERT and SELECT only on this table.
- `app.audit.service.record(db, actor, action, target_type, target_id, result, details)`, writing in the caller's transaction so the audit and the change commit together.
- Action names use `module.verb`, for example `accounts.login`, `content.submit` or `settings.update`.
- An index on `occurred_at` and on `(target_type, target_id)`.
- Wire `set_setting` from `P0-SET-02` to record changes.

The Admin audit search screen is built in `P3-UI-01`.

**Security**

- `details` never contains passwords, tokens, codes or secrets. `record()` drops known sensitive keys, and a test proves it.
- Every Member action records the session ID and IP, so actions remain traceable even though the login is shared (SRS 2.3).

**Acceptance criteria**

- [ ] An attempt to UPDATE or DELETE an audit row fails at the database
- [ ] An audit row is written in the same transaction as the change, and a rolled-back change leaves no audit row
- [ ] Changing a setting writes an audit event with old and new values

**Tests:** `test_fr_12_1_audit_rows_cannot_be_updated`, `test_fr_12_1_audit_rows_cannot_be_deleted`, `test_fr_4_6_audit_rolls_back_with_change`, `test_p1_aud_01_sensitive_keys_dropped`.

---

### P1-UI-01 — Build the accessible base layout and role dashboard shells

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P0-SET-01` | SRS 4.1, 5.5, [conventions.md](../conventions.md) interface rules |

**Goal:** every later page reuses one accessible layout and one set of form components.

**Scope**

- `templates/base.html` with a header, a navigation menu per login type, a skip link, `main` and `nav` landmarks, a footer, and a place for flash messages.
- `templates/macros/forms.html` with field macros: label, input, help text and an error linked by `aria-describedby`.
- Error pages for 403, 404 and 500 that reveal no internal details.
- Tailwind CSS, compiled from `static/css/app.src.css` by the npm CLI at build time (Tailwind replaced Bootstrap 5 in this task). HTMX is vendored into `static/vendor/` with the first page that uses it.
- `_()` translation wrapping set up through Jinja's i18n extension, English only.
- Empty dashboard pages for Member, Admin, Reviewer and Approver, linked from the navigation.

**Security**

- Jinja autoescaping is on for every template.
- No inline scripts or styles, so the Content Security Policy can stay strict.
- Error pages never show stack traces, including when the app runs in debug mode on staging.

**Acceptance criteria**

- [ ] The layout passes an automated axe check with no serious or critical issues
- [ ] Every page can be used by keyboard alone, with a visible focus indicator
- [ ] A 500 error shows the friendly page, and the trace appears only in server logs

**Tests:** `test_p1_ui_01_error_pages_hide_details`, plus a Playwright axe check of the dashboards.

---

### P1-UI-02 — Build the design system: tokens, components and motion rules

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P1-UI-01`, `P1-ACC-08` | SRS 5.5, Q-11, [conventions.md](../conventions.md) UI and motion rules, `.claude/skills/apple-design` |

**Goal:** one set of visual building blocks that every page uses, so the portal looks and moves the same everywhere, however many developers and AI tools build it.

**Scope**

- `static/css/tokens.css`: every design value as a CSS variable, in light and dark variants:
    - colour: surfaces, text, borders, brand accent, and status colours (success, warning, danger, info)
    - spacing scale in `rem`, corner radii and two shadow depths
    - type scale using the `system-ui` font stack, with line height and letter-spacing per size (tighter on large headings, none on body text)
    - motion: three durations (150, 200 and 300 ms) and two easing curves, one for entering and one for leaving
- Expose the tokens to Tailwind as theme variables (`@theme` in `static/css/app.src.css`), so utility classes use them and no page needs a one-off value.
- `static/css/components.css` and `templates/macros/ui.html` with these components:
    - button (primary, secondary, danger and link)
    - card and item card
    - badge, including the lock label "Available to member Discoms – log in"
    - alert and flash message
    - modal using the native `<dialog>`, and a side drawer
    - empty state, skeleton loader and pagination
- Instant press and focus feedback (`:active`, `:focus-visible`) on every interactive component. Pressed controls shrink slightly and settle back.
- Page transitions with the View Transitions API (`@view-transition { navigation: auto; }`), and HTMX swaps set to use transitions.
- A dashboard of a greeting and panels: key figures that link to their pages, quick links and the login's two-step sign-in status.
- Every button has an icon. Closing a dialog and per-row actions show the icon alone, with an accessible name.
- A select component over the native select: search above 10 options, options from a server address with search and infinite scroll, and a list that opens where there is room.
- Toasts for the result of an action, rising at the bottom centre: small, like a tooltip; success and note close after 3 seconds, warning and error after 6, pausing under the pointer or focus.
- Selectable tables: checkboxes, a bar of actions for the ticked rows (copy, CSV export) and a right-click row menu. Actions that change records are not part of this task.
- A data table component: search, a header that stays while rows scroll, a height that fits the screen on wide screens, and a row count.
- A translucent top bar with `backdrop-filter` and a solid fallback.
- A theme button on every page that switches between light and dark in one click, remembered in the browser. Light is the default.
- Signed-in pages float: a light sidebar with folding sections and a page finder, a row with the breadcrumb pill (menus for pages, and a button that hides the sidebar) and the page actions, then cards on the canvas. The breadcrumbs name the page, so page headings are for screen readers.
- `prefers-reduced-motion`, `prefers-reduced-transparency` and `prefers-contrast: more` handled once, in the tokens, so no component needs its own check.
- A style-guide page at `/_styleguide` showing every token and component, in light and dark, for review by ITPED and the designer.
- If a designer supplies mock-ups (Q-11), take colours, radii and spacing from them. If not, build the clean default and record that in [decisions.md](../decisions.md).

Later pages only reuse these components. A new component is added here, not inside a feature template.

**Security**

- No inline styles or scripts, and no CDN files, so the Content Security Policy stays strict (`style-src 'self'`, `script-src 'self'`).
- The style guide is for privileged users only, and returns 404 to Members and visitors.

**Acceptance criteria**

- [ ] The style guide shows every token and component, in light and dark mode
- [ ] axe reports no serious or critical issues on the style guide in either mode, and every text and background pair meets WCAG AA contrast
- [ ] With reduced motion set, transitions become a short cross-fade or none
- [ ] With reduced transparency set, the top bar and scrims become solid
- [ ] `P1-UI-01` pages use the new components, with no one-off colours, sizes or animations left

**Tests:** `test_p1_ui_02_styleguide_privileged_only`, plus Playwright checks `test_p1_ui_02_axe_light_and_dark` and `test_p1_ui_02_reduced_motion` (with `reducedMotion: "reduce"` emulated).

---

### P1-ACC-08 — Add the four login types and role guards

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P0-ARC-01`, `P1-AUD-01` | FR-2.1, FR-2.2, FR-2.4, [security.md](../security.md) access control |

**Goal:** exactly four login types exist, and every route declares who may use it.

**Scope**

- A `login` table with these fields:
    - `user_id`: unique and case-insensitive, 4 to 50 characters of `a-z`, `0-9`, `.`, `_` and `-`
    - `email`, `password_hash`
    - `login_type`: `member`, `admin`, `reviewer` or `approver`
    - `organisation_id`: required for Members, optional for a Reviewer from a Discom
    - `full_name`: required for privileged logins
    - `is_alternate`: Reviewers only
    - `status`: `pending`, `active`, `declined` or `deactivated`
    - MFA fields and lockout fields, added by later tasks
- A partial unique index allowing one `pending` or `active` Member login per organisation (FR-2.2).
- `app.accounts.guards.require_login_type(*types)`, a FastAPI dependency that returns the current login or refuses the request.
- A route registry test that fails if any route lacks either `require_login_type` or an explicit `public_route` marker.

**Security**

- No route, form or API creates any other login type (FR-2.1).
- An anonymous request to a protected page redirects to login. A logged-in user with the wrong type gets 403, and the refusal is audited with `result = denied`.

**Acceptance criteria**

- [ ] The database refuses a second active Member login for the same Discom
- [ ] Each protected route refuses each wrong login type
- [ ] The route registry test fails when a new unguarded route is added

**Tests:** `test_fr_2_1_only_four_login_types`, `test_fr_2_2_one_member_login_per_discom`, `test_p1_acc_08_every_route_is_guarded`, plus a parameterised refusal test across all guarded routes.

---

### P1-ACC-04 — Add password policy, lockout and failed-attempt logging

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P1-ACC-08` | FR-1.7, [security.md](../security.md) authentication |

**Goal:** strong passwords, brute-force protection and a full record of failed sign-ins.

**Scope**

- `app/accounts/passwords.py` with:
    - `hash_password(plain)` using argon2id
    - `verify_password(hash, plain)`, which rehashes when the parameters change
    - `check_password_policy(plain, user_id)`, requiring at least 12 characters with at least one letter, one number and one symbol, and refusing a password containing the User ID
- A `login_attempt` table: `attempted_user_id`, `login_id` (nullable), `ip`, `user_agent`, `success`, `reason` and `at`.
- Lockout fields on `login`: `failed_count` and `locked_until`.
- Service functions:
    - `record_failed_attempt(db, login, ip, user_agent)`: after 5 consecutive failures, sets `locked_until` to now plus 15 minutes and audits the lockout
    - `record_success(db, login)`: resets the counter
    - `is_locked(login)`

**Security**

- Unknown User IDs are logged as failed attempts, and the login screen shows the same message as for a wrong password.
- Counting is done with a row lock, so parallel attempts cannot get around the limit.
- Note risk R-08: anyone who knows a Discom's User ID can trigger the 15-minute lockout.

**Acceptance criteria**

- [ ] An 11-character password, or one missing a letter, number or symbol, is refused with a clear message
- [ ] The 5th consecutive failure locks the account for 15 minutes, and the correct password is refused during the lockout
- [ ] Every failed attempt is stored in `login_attempt`, including unknown User IDs
- [ ] A successful sign-in resets the counter

**Tests:** `test_fr_1_7_password_minimum_length`, `test_fr_1_7_password_character_mix`, `test_fr_1_7_lockout_after_five_failures`, `test_fr_1_7_lockout_expires_after_15_minutes`, `test_fr_1_7_failed_attempts_logged`, `test_p1_acc_04_parallel_failures_counted`.

---

### P1-ACC-06 — Build server-side sessions, CSRF protection and idle timeout

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P1-ACC-04` | FR-1.7, SRS 2.3, [security.md](../security.md) sessions |

**Goal:** a secure sign-in, a session that ends after 30 idle minutes, and protection against forged requests.

**Scope**

- Sign-in and sign-out pages and routes using `verify_password`, the lockout functions and the generic error message.
- A `user_session` table: `id`, `token_hash`, `login_id`, `csrf_token`, `mfa_pending`, `created_at`, `last_seen_at`, `ended_at`, `end_reason` (`logout`, `idle`, `replaced`, `admin` or `password_reset`), `ip` and `user_agent`.
- `app/core/sessions.py` middleware that:
    - loads the session from the `drr_session` cookie
    - ends it if idle for more than 30 minutes
    - updates `last_seen_at`, at most once a minute
- CSRF protection: a per-session token, a Jinja `csrf_field()` macro and an HTMX header. Every POST, PUT, PATCH and DELETE is checked.
- A new token is issued at sign-in, so the session ID changes on login.

**Security**

- The cookie is `HttpOnly`, `Secure` and `SameSite=Lax`, with no `Domain`.
- Only the SHA-256 hash of the token is stored.
- Any sign-out or session end is effective immediately on the next request.
- Every sign-in, sign-out and idle end is audited with session ID and IP.

**Acceptance criteria**

- [ ] A session idle for 31 minutes is refused and redirects to sign-in
- [ ] A form POST without a valid CSRF token gets 403
- [ ] The session token changes at sign-in
- [ ] The cookie flags are as specified

**Tests:** `test_fr_1_7_idle_session_ends_after_30_minutes`, `test_p1_acc_06_csrf_required_on_post`, `test_p1_acc_06_token_rotates_on_login`, `test_p1_acc_06_cookie_flags`, `test_p1_acc_06_token_stored_hashed`.

---

### P1-ACC-07 — Enforce the 5-device limit with the sixth-session policy

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P1-ACC-06` | FR-2.3, D-10, SRS 5.1 |

**Goal:** a Member login is active on at most five devices, and Admin decides what happens on the sixth.

**Scope**

- At Member sign-in, count active sessions while holding a row lock on the login.
- If 5 are active, apply `sixth_session_policy`:
    - `block` (default, D-10): refuse with "This Discom login is already signed in on 5 devices. Sign out on another device or contact ITPED."
    - `end_oldest`: end the oldest session with reason `replaced`
- An Admin setting screen for the policy.
- A Member "Signed-in devices" page listing active sessions (device, IP, last activity), with sign-out for each.

**Security**

- Each refusal and each replaced session is audited.
- A Member can end only its own sessions.

**Acceptance criteria**

- [ ] Five sessions work at once
- [ ] With `block`, the sixth sign-in is refused and the five continue
- [ ] With `end_oldest`, the sixth succeeds and the oldest is ended
- [ ] Six parallel sign-in attempts never produce six active sessions

**Tests:** `test_fr_2_3_five_sessions_allowed`, `test_fr_2_3_sixth_blocked`, `test_fr_2_3_sixth_ends_oldest`, `test_fr_2_3_parallel_logins_never_exceed_five`.

---

### P1-ACC-09 — Build privileged account management

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P1-ACC-06` | FR-2.7, SRS 2.3 |

**Goal:** Admin can manage named Admin, Reviewer and Approver accounts, and the first Admin can be created safely.

**Scope**

- A command-line command `python -m app.accounts.cli create-admin` for the first Admin, run on the server only.
- Admin screens to:
    - create an Admin, Reviewer or Approver with full name and email
    - deactivate an account, ending its sessions at once
    - reassign: deactivate one person and create the replacement, moving their open assignments
    - mark Reviewers as primary or alternate
- A new account receives a single-use set-password link, valid for 60 minutes.
- Rules:
    - one active Approver at a time (the Centre Director)
    - one active primary and one active alternate Reviewer
    - Admin cannot deactivate their own account

**Security**

- No shared privileged accounts: each has a named person and their own email (FR-2.7).
- The set-password token is stored hashed and expires after 60 minutes.
- Every create, deactivate and reassign is audited.

**Acceptance criteria**

- [ ] A created account can set its password once, and the link fails on reuse or after 60 minutes
- [ ] A second active Approver is refused
- [ ] Deactivation ends that account's sessions immediately
- [ ] Only Admin can reach these screens

**Tests:** `test_fr_2_7_admin_creates_privileged_accounts`, `test_fr_2_7_single_active_approver`, `test_fr_2_7_deactivation_ends_sessions`, `test_p1_acc_09_set_password_link_single_use`.

---

### P1-ACC-10 — Add MFA by authenticator app and email code

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | `P1-ACC-06`, `P1-ACC-09` | FR-2.8, [security.md](../security.md) authentication |

**Goal:** every privileged sign-in needs a second factor, and Members can choose to use one.

**Scope**

- Enrolment with an authenticator app (TOTP, through pyotp), with a QR code and a manual key.
- Email codes: 6 digits, valid for 10 minutes, single use, maximum 5 tries.
- Sign-in flow: after the password check, the session has `mfa_pending = true` and can reach only the code page. After a correct code, the token rotates and `mfa_pending` is cleared.
- Privileged logins must enrol at their first sign-in. Members can turn MFA on or off in their profile.
- Admin can reset another person's MFA. An Admin's own MFA is reset by a second Admin.

**Security**

- TOTP secrets are encrypted with a key from the environment, using `cryptography` Fernet.
- A session with `mfa_pending` cannot reach any other route. Test every privileged route.
- Code attempts are rate limited and audited.

**Acceptance criteria**

- [ ] An Admin, Reviewer or Approver cannot reach any page without completing MFA
- [ ] A wrong, expired or reused code is refused
- [ ] A Member without MFA signs in with a password only
- [ ] An MFA reset is audited

**Tests:** `test_fr_2_8_privileged_mfa_required`, `test_fr_2_8_pending_mfa_blocks_all_routes`, `test_fr_2_8_email_code_expires`, `test_fr_2_8_code_single_use`, `test_fr_2_8_member_mfa_optional`, `test_p1_acc_10_totp_secret_encrypted`.

---

### P1-ACC-01 — Build the Discom master list and Admin screen

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P1-ACC-08`, `P1-ACC-09` | FR-1.6, Q-09 |

**Goal:** Admin maintains the list of recognised Discoms that registration is checked against.

**Scope**

- An `organisation` table: `name` (unique), `email_domain` (unique, lowercase), `status` (`active` or `inactive`), `created_at` and `updated_at`.
- Admin screens to list, add, edit and deactivate Discoms.
- A CSV import for the list of 70 Discoms (Q-09), with a preview before saving and errors listed per row.
- Seed three test Discoms in development and staging only.

**Security**

- Admin only. Every change is audited.
- A deactivated Discom cannot register, and its Member login cannot sign in.

**Acceptance criteria**

- [ ] Admin can add, edit, deactivate and import Discoms
- [ ] A duplicate name or domain is refused
- [ ] An inactive Discom's Member login cannot sign in

**Tests:** `test_fr_1_6_master_list_crud`, `test_fr_1_6_duplicate_domain_refused`, `test_fr_1_6_inactive_discom_blocked`.

---

### P1-ACC-02 — Build the registration form with CAPTCHA

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P1-ACC-01`, `P1-ACC-04`, `P0-SEC-01` | FR-1.1, FR-1.2, D-11, SRS 5.7 |

**Goal:** a Discom can request its single Member login through a public, bot-protected form.

**Scope**

- A public "Register your Discom" flow in three steps:
    1. Discom (chosen from active organisations), official email address and the CAPTCHA
    2. the 6-digit code emailed to that address
    3. desired User ID, password and confirmation
- Step 3 suggests User IDs that are free, and says whether a typed one is free.
- Reserved User IDs: format rules, words refused anywhere or as a whole part (seen through separators, number tails, look-alike digits, doubled letters and plurals), and each Discom's bracketed code kept for that Discom. Admin adds and removes words on a Reserved IDs screen. The rules also apply to staff accounts an Admin creates; existing logins are unchanged.
- The CAPTCHA from `P0-SEC-01` ([decision record 0006](../adr/0006-self-hosted-captcha.md)):
    - a public route that returns `app.core.captcha.new_challenge()` as JSON
    - the ALTCHA widget's `dist/external` build, its CSS and workers, served from `static/vendor/`
    - `app.core.captcha.verify()` called on submit, reused everywhere else a CAPTCHA is needed
- Validation:
    - the email domain matches the Discom's domain (D-11); only then is a code sent
    - the User ID is unique and well formed
    - the password passes `check_password_policy`
    - the Discom has no pending or active Member login (FR-1.6)
- Until step 3 is sent, the request is kept only in Redis and expires on its own.
- On success, create a `pending` Member login and show "Your request has been sent to ITPED for verification."
- Show the privacy notice wherever personal data is collected: what is collected, why and for how long (SRS 5.7).

**Security**

- The CAPTCHA is checked on the server before any other processing.
- Registration is rate limited per IP in Nginx.
- Step 1 answers the same way whether or not a code was sent, so it cannot be used to learn Discom domains or who has a login. The email is sent after the answer, so timing does not tell.
- A code is 6 digits, lasts 10 minutes, allows 5 tries and is sent at most once a minute to an address. Only its hash is stored.
- Whether a User ID is taken is told only to a visitor who has entered the code, for 30 minutes and at most 30 checks.
- Each request is audited.

**Acceptance criteria**

- [ ] A solved CAPTCHA, the emailed code and a valid form create a pending Member login
- [ ] An unsolved or replayed CAPTCHA is refused
- [ ] An address outside the Discom's domain is sent no code and gets the same page
- [ ] No later step works without the code
- [ ] A suggested User ID is free and allowed
- [ ] A reserved User ID, however disguised, is refused at registration and for staff accounts
- [ ] Admin can add and remove reserved words, and each change is audited
- [ ] A second request for a Discom with a pending or active login is refused
- [ ] The privacy notice is shown where data is collected

**Tests:** `test_fr_1_1_registration_creates_pending_login`, `test_fr_1_2_captcha_required`, `test_fr_1_6_duplicate_registration_refused`, `test_d11_only_the_discoms_domain_is_sent_a_code`, `test_p1_acc_02_later_steps_need_a_proved_email`.

---

### P1-ACC-03 — Build Admin verification, activation and notification

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P1-ACC-02` | FR-1.3, FR-1.4, FR-1.6 |

**Goal:** ITPED Admin confirms each registration before the Discom can sign in.

**Scope**

- An Admin queue of pending registrations, showing the Discom, email, User ID and request time.
- Admin actions:
    - Approve: status becomes `active`, and an email goes to the registered address
    - Decline: a reason is required, and an email goes to the address
- `app/core/email.py` with `send_email(to, subject, template, context)`, sent through Celery with retries. Reuse it everywhere else.
- Email templates for activation and decline, in both HTML and plain text.

**Security**

- Only Admin can approve. Each decision is audited.
- Emails contain no password and no sign-in link with a token.

**Acceptance criteria**

- [ ] An approved Discom can sign in, and a pending one cannot
- [ ] Approval and decline each send the right email
- [ ] A failed email send is retried and logged, and does not block approval

**Tests:** `test_fr_1_3_pending_login_cannot_sign_in`, `test_fr_1_4_activation_sends_email`, `test_fr_1_3_decline_requires_reason`.

---

### P1-ACC-05 — Build password reset with CAPTCHA

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P1-ACC-03`, `P1-ACC-04` | FR-1.2, FR-1.5 |

**Goal:** a Discom can reset its password without contacting ITPED.

**Scope**

- A "Forgot password" form asking for the User ID or registered email, protected by CAPTCHA.
- If the account exists and is active, email a single-use reset link valid for 60 minutes.
- A reset page that applies the password policy.
- A successful reset ends all of that login's sessions and clears any lockout.

**Security**

- The response is always "If an account matches, we have sent a link", whether or not it exists.
- The reset token is stored hashed and is single use.
- Requests are rate limited per IP and per account. Each request and reset is audited.

**Acceptance criteria**

- [ ] A valid reset link sets a new password once, and fails on reuse or after 60 minutes
- [ ] Resetting ends all existing sessions for that login
- [ ] The form response does not reveal whether an account exists

**Tests:** `test_fr_1_5_reset_link_single_use`, `test_fr_1_5_reset_link_expires`, `test_fr_1_5_reset_ends_sessions`, `test_fr_1_2_reset_requires_captcha`, `test_fr_1_5_no_account_enumeration`.

---

### P1-SEC-01 — Human line-by-line review of login, sessions and audit

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev (tech lead or security reviewer) | All other Phase 1 Dev tasks | [security.md](../security.md), R-04 |

**Goal:** a person who did not write the code reads every line of the most sensitive Phase 1 code before Phase 2 builds on it.

**Scope**

Review `app/accounts`, `app/core/sessions.py`, `app/core/captcha.py` and `app/audit` against this checklist:

- [ ] Password hashing uses argon2id, and comparisons are constant-time
- [ ] Session tokens use enough randomness, are stored hashed, rotate at sign-in and MFA, and have the right cookie flags
- [ ] Every state-changing route checks CSRF
- [ ] Lockout counting is race-free
- [ ] No response or message reveals whether an account exists
- [ ] A session with `mfa_pending` cannot reach anything except the code page
- [ ] Every Admin route is guarded, and refusals are audited
- [ ] No password, token, code or secret is logged or stored in audit details
- [ ] Reset and set-password tokens are hashed, single use and expire

**Security**

- Record findings as `DEF-###` defects with severities. S1 and S2 findings are fixed before Phase 2 starts.

**Acceptance criteria**

- [ ] The completed checklist and findings are attached to the review pull request
- [ ] No S1 or S2 finding remains open

**Tests:** add a regression test for every defect found.

---

### P1-QA-01 — Test registration, activation, lockout and reset

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | `P1-ACC-02`, `P1-ACC-03`, `P1-ACC-04`, `P1-ACC-05` | AC-01, AC-04, FR-1 |

**Goal:** end-to-end proof that FR-1 works on staging.

**Scope**

- Playwright tests for:
    - registration with a valid and an invalid CAPTCHA (AC-01)
    - Admin activation and decline, including the emails
    - lockout after 5 failures and unlock after 15 minutes (AC-04)
    - logout after 30 idle minutes, with time controlled in the test environment (AC-04)
    - password reset, including link reuse and expiry
- Exploratory testing of error messages for account enumeration.

**Security**

- Confirm the sign-in, registration and reset responses never reveal whether an account exists.

**Acceptance criteria**

- [ ] AC-01 and AC-04 pass on staging
- [ ] All tests are in the nightly regression pack

**Tests:** `tests/e2e/test_registration.py`, `tests/e2e/test_lockout_and_reset.py`.

---

### P1-QA-02 — Test sessions, sixth-session handling, MFA and role refusals

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | QA | `P1-ACC-06` to `P1-ACC-10` | AC-02, AC-03, FR-2 |

**Goal:** end-to-end proof that FR-2 access controls work on staging.

**Scope**

- Five concurrent Member sessions in separate browser contexts, then a sixth under each policy (AC-03).
- MFA enrolment and sign-in for each privileged type, with a wrong code and an expired code (AC-02).
- Each login type trying each other type's pages, expecting refusal.
- Privileged account creation, deactivation and reassignment.

**Security**

- Try to reach privileged pages while MFA is pending, by typing URLs directly.

**Acceptance criteria**

- [ ] AC-02 and AC-03 pass on staging
- [ ] Every refusal case passes

**Tests:** `tests/e2e/test_sessions.py`, `tests/e2e/test_mfa.py`, `tests/e2e/test_role_refusals.py`.

---

### P1-QA-03 — Build the baseline Playwright regression pack

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | QA | `P1-QA-01`, `P1-QA-02` | SRS 8 |

**Goal:** one command runs all end-to-end tests, and every later phase adds to it.

**Scope**

- Organise the end-to-end tests into a `regression` marker, with an HTML report published by the nightly CI job.
- Add a failure notification to the team channel.
- Document how to run the pack locally and against staging in `docs/test-plan.md`.

**Security**

- None specific.

**Acceptance criteria**

- [ ] The nightly job runs the pack and publishes a report
- [ ] A failing test notifies the team

**Tests:** the pack itself.
