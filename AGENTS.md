# AGENTS.md

Rules for every developer and every AI coding tool working in this repository. Read this before writing code.

The sections below are copied from [docs/conventions.md](docs/conventions.md) and [docs/security.md](docs/security.md), which are the source. If you change a rule, change it there and copy it here in the same pull request.

## Before you start a task

1. Find the task spec in [docs/tasks/](docs/tasks/README.md). Build only what its Scope says.
2. Check its **Depends on** tasks are Done.
3. Branch `type/<task-code>-short-description`, for example `feat/p1-acc-04-password-lockout`.
4. Copy `docs/journal/_template.md` to `docs/journal/<CODE>.md`, set Status to `In progress`, and commit it first. Keep it updated in the same pull request as the code: log, decisions, deviations, status. See [docs/journal/README.md](docs/journal/README.md).
    - Coming back to a task later, even after it is Done (review fix, bug fix, follow-up, refactor, a `DEF-###`), always add a log line and any new decision to that task's journal file in the same pull request, and set it back to `In progress` if the change reopens its acceptance criteria. Never change a task's code without updating its journal.
    - Keep the [shared planning tracker](https://claude.ai/artifact/LnUnS1xkX7cgrTGuwDgY7q) in step with the repository. When a pull request changes a task's status, adds, removes or re-scopes a task, changes its points or dependencies, or adds or changes a decision (`D-##`) or open question (`Q-##`), update the matching rows and totals in the tracker when the pull request opens and again when it merges, and note it in the journal log line. Change the repository first and copy to the tracker, never the other way round.
5. Commit subjects start with the task code: `P1-ACC-04: Lock account after five failed sign-ins`.
6. No AI attribution lines in commits, pull requests or code comments.


## Coding rules

**Structure**

- Every module under `app/` has the same four files: `router.py` (HTTP only), `service.py` (business rules), `models.py` (tables) and `schemas.py` (Pydantic). Small helpers can live in extra files in the same module.
- Routes stay thin: they parse input, call one service function and render a response.
- Business rules live only in `service.py` functions, which take `db` and `actor` explicitly.
- Use plain `def` routes and synchronous SQLAlchemy. Do not use `async def` unless a task says so.

**Readability**

- Prefer short functions that do one thing, descriptive names, early returns and simple control flow.
- Avoid clever one-liners, dense comprehensions, nested ternaries and metaprogramming.
- Ruff's complexity check (C901) fails the build for any function above 10.
- Every public function has type hints and a one-line docstring.
- Comments explain the reason, not the action, and cite the requirement, for example `# FR-13.3: teasers must never expose the file name`.

**Reuse, never copy**

- **Never write the same code twice.** This covers Python, templates, JavaScript, styles and tests. Search before writing; the second time a piece of logic or markup is needed, move it to one shared place (a function, a macro, a helper) in the same change. Override a style by editing its rule, not by adding a second rule further down.
- **Check for it before calling a task finished.** Read the whole diff for copies and near-copies, fix them, and list in the pull request any you leave and why. `tests/core/test_design_system.py` catches repeated styles; the rest is checked by reading.

Before writing a helper, search the codebase. These shared functions must be used instead of reimplemented:

| Need | Use | Created in |
| --- | --- | --- |
| Write an audit event | `app.audit.service.record()` | `P1-AUD-01` |
| Get a database session in a route | `app.core.db.DbSession` (commits before the response is sent) | `P0-SET-02` |
| Read a configurable setting | `app.core.settings_store.get_setting()` | `P0-SET-02` |
| Get the current time or show it in IST | `app.core.time.utc_now()` and `to_ist()` | `P0-SET-02` |
| Check who may see or open an item | `app.content.visibility` functions | `P2-CON-06` |
| Change a workflow state | `app.workflow.service.apply_action()` | `P2-WF-01` |
| Require a login type on a route | `app.accounts.guards.require_login_type()` | `P1-ACC-08` |
| Mark a route open to visitors | `dependencies=[Depends(app.accounts.guards.public_route)]` | `P1-ACC-08` |
| Describe the signed-in login for an audit event | `app.accounts.guards.actor_for()` | `P1-ACC-08` |
| Describe a visitor who is not signed in for an audit event | `app.accounts.guards.visitor_actor()` | `P1-ACC-02` |
| Hash, check or validate a password | `app.accounts.passwords` (`hash_password`, `verify_password`, `check_password_policy`) | `P1-ACC-04` |
| Check that a User ID is allowed | `app.accounts.user_id_rules` (`shape_problem`, `is_reserved`); words come from `app.accounts.service.reserved_words()` | `P1-ACC-02` |
| Check a sign-in, with lockout and attempt logging | `app.accounts.service.authenticate()` | `P1-ACC-04` |
| Start or end a session, with its cookie and audit | `app.core.sessions.start_session()` and `end_session()` | `P1-ACC-06` |
| Put the CSRF token in a form | `csrf_field()` in `templates/macros/forms.html`, imported `with context` | `P1-ACC-06` |
| Issue and verify a CAPTCHA | `app.core.captcha.new_challenge()` and `verify()`; on a page, `<altcha-widget challenge="/captcha/challenge">` with `static/js/captcha.js` (see `accounts/register.html`) | `P0-SEC-01`, `P1-ACC-02` |
| Send an email | `app.core.email.send_email()` (`P1-ACC-03` moves sending to Celery with retries) | `P1-ACC-09` |
| Issue or check a single-use emailed link | `app.accounts.tokens` (`issue_link_token`, `usable_token`, `mark_used`) | `P1-ACC-09` |
| Issue or check an emailed sign-in code | `app.accounts.tokens` (`issue_email_code`, `use_email_code`) | `P1-ACC-10` |
| Decide whether a login needs a second factor, and check one | `app.accounts.service` (`needs_mfa`, `finish_mfa`) | `P1-ACC-10` |
| Create a notification | `app.workflow.notifications.notify()` | `P2-WF-05` |
| Serve a protected file | `app.content.delivery.protected_file_response()` | `P3-VIEW-03` |
| Render a page | `app.core.templates.templates`, with the page extending `templates/base.html` | `P1-UI-01` |
| Render a form field with its label, help and error | `templates/macros/forms.html` | `P1-UI-01` |
| Offer a choice from a list | `select()` in `templates/macros/forms.html`, never a bare `<select>` (`static/js/select.js` adds search over 10 options, server paging and placement) | `P1-UI-02` |
| Add a menu entry for a login type | `app.core.navigation` | `P1-UI-01` |
| Show where a signed-in page sits (breadcrumbs) | `app.core.navigation.breadcrumbs()`, passed to the page as `breadcrumbs` | `P1-UI-02` |
| Render a button, card, badge, modal or other UI element | `templates/macros/ui.html` and the tokens in `static/css/tokens.css` | `P1-UI-02` |
| Offer the light or dark theme | `theme_switcher()` in `templates/macros/ui.html` (works through `static/js/shell.js`) | `P1-UI-02` |
| Open a menu from a button | `menu_panel()` and `page_items()` in `templates/macros/ui.html`, opened with `popovertarget` | `P1-UI-02` |
| List records in a table | `data_table()` in `templates/macros/ui.html` (search, fixed header, fits the screen height, row count; `compact` for long narrow lists, `batch` to show rows as the reader scrolls). With `columns`, and `data-export` and `data-copy` on each row, it adds checkboxes, copy and CSV export, and a row menu (`static/js/table.js`) | `P1-UI-02` |
| Put a page's actions beside the breadcrumbs | `{% block page_actions %}` in a page that extends `templates/base.html` (see `accounts/admin_discoms.html`) | `P1-UI-02` |
| Render a sign-in, registration or other page shown before signing in | Extend `templates/layouts/auth.html` and start with `auth_heading()` | `P1-UI-02` |

**Avoid hidden behaviour**

- Do not use event listeners that change data behind the caller's back, such as SQLAlchemy events for business rules.
- Do not use global mutable state.
- Do not use magic dependency chains that hide what a route needs.

**Configuration**

- Values the SRS says Admin can change live in the `app_setting` table and are read through `get_setting()`. See the settings table in [architecture.md](docs/architecture.md).
- Values the SRS fixes, such as the 12-character password minimum, are constants in `app/core/constants.py`, each with an FR reference.
- Secrets come only from environment variables. Never commit `.env` files.

**Data rules**

- Store all timestamps in UTC as `timestamptz`, and display them in India Standard Time.
- Never hard-delete content, expert or Gallery records. Use states or flags instead (SRS 6.3).
- The only hard deletion is expert personal data after consent withdrawal (`FR-8.3`).
- Every migration has a downgrade path, or a written reason in the pull request why it cannot have one.

**Interface rules**

- Pages meet WCAG 2.1 AA: labels on every input, visible focus, landmarks, a skip link, and errors linked to their fields.
- Wrap user-facing text in `_()` so Hindi can be added later (SRS 5.5).
- Never render an admin-only field in a Member or public template. Pass view schemas that do not contain those fields (`P2-CON-02`).

**Confirm before anything serious**

Any action that removes, deactivates, resets, grants or changes who can do what asks first, everywhere in the system. Put `data-confirm`, `data-confirm-title` and `data-confirm-action` on its form; `static/js/shell.js` shows the shared dialog and sends nothing until the person agrees. Say what will happen and whether it can be undone. If another step already confirms it, mark the form `data-confirmed-by` (`dialog`, `checkbox` or `preview`). A form that is not serious is listed in `SAFE_ACTIONS` in `tests/core/test_ui_rules.py`, and that test fails for any other.

**Checks every UI change must pass**

A change that adds or alters a page, component or message is not finished until these hold. Where a test can check a rule, it does; add to that test when you add a page, and add a rule here when a UI defect gets through review.

| Rule | Checked by |
| --- | --- |
| A result is announced once: any `?done=`-style name a redirect adds is removed from the address by `forgetResult()` in `static/js/shell.js` | `tests/core/test_ui_rules.py` |
| A message's colour matches what happened: success, note, warning or failure. A change that takes something away (deactivate, delete, reset, turn off) is a warning, never a plain success | `tests/core/test_ui_rules.py` |
| Choices use `select()`, not a bare `<select>` | `tests/core/test_ui_rules.py` |
| Every button has an icon | `tests/core/test_design_system.py` |
| No script errors, no sideways scroll and no control stuck at its pressed size, on desktop and phone widths | `tests/e2e/test_ui_health.py` |
| Light and dark both pass axe | `tests/e2e/` |
| Do the action in a browser, then reload the page and press Back: nothing repeats or reappears | By hand, noted in the pull request |

**UI and motion rules**

The `apple-design` skill in [`.claude/skills/`](.claude/skills/apple-design/SKILL.md) is the reference for look and feel. These rules decide what applies here, and win over the skill in any conflict.

- Build every page from the design-system tokens (CSS variables) and component macros. No one-off colours, sizes, shadows or animations.
- Give feedback immediately: style `:active` and `:focus-visible` states, and show an HTMX loading indicator for any request that may take longer than about 300 ms.
- Animate only `transform` and `opacity`, for 150 to 300 ms. The one exception is the sidebar hiding and showing: a 400 ms glide (`--aida-duration-glide`), as a view transition. Motion must never delay content: the page renders first and motion adds polish.
- Motion settles softly with no overshoot (`--aida-ease-settle`). Pressable controls shrink slightly and return; add a new control to the press rule in `components.css`.
- Use CSS transitions and the View Transitions API (`hx-swap="... transition:true"` for HTMX swaps). Spring or animation libraries need tech lead approval and are only for real gesture features.
- Do not add drag, flick or rubber-band physics, sound or haptics to the web portal.
- Open and close modals, drawers and menus along the same path, and from the control that opened them.
- Use translucent glass (`backdrop-filter`) for the panels of signed-in pages (sidebar, cards, breadcrumb bar), menus, dialogs, the top bar and modal scrims, through `--aida-surface-glass` and `--aida-glass`. Text on it must pass WCAG AA contrast, with a solid fallback.
- Respect `prefers-reduced-motion` (switch to a short cross-fade or no motion), `prefers-reduced-transparency` (solid surfaces) and `prefers-contrast: more` (solid surfaces, stronger borders). Nothing may flash more than three times a second.
- Use the `system-ui` font stack, with size in `rem`, tighter letter-spacing on large headings and none on body text. Do not use Apple's SF Pro font files on the web, and do not copy Apple's own designs, icons or assets.
- Keep the tone calm and professional: no confetti, bouncing or attention-seeking motion on a governed knowledge portal.

**New libraries**

Only the libraries listed in [architecture.md](docs/architecture.md) are approved. To add another, get tech lead approval and add it to that list in the same pull request.

## Testing

- **Unit and integration:** pytest with a real PostgreSQL test database. Do not mock the database.
- **End to end:** Playwright against staging, using the role logins from the test data (`P0-QA-02`).
- **Naming:** `test_fr_<n>_<m>_<behaviour>`, for example `test_fr_13_3_teaser_hides_file_name`. Tests without an FR use the task code, for example `test_p2_con_06_ambiguous_tier_defaults_to_restricted`.
- **Refusals:** every permission rule needs a test proving the wrong role is refused.
- **Location:** `tests/<module>/test_<topic>.py`.

## Security-sensitive areas

Changes in these areas need two reviewers, one of them the tech lead or the security reviewer. Apply the `security` label on the pull request.

- Login, passwords, sessions, CSRF and MFA (`app/accounts`, `app/core/sessions.py`)
- Item visibility and file delivery (`app/content/visibility.py`, `app/content/delivery.py`)
- Uploads, scanning and the tusd hooks (`app/content/uploads.py`)
- Audit (`app/audit`)
- Public pages and anything that renders Restricted item data (`app/public`)

## Mandatory security controls

### Authentication and sessions

- Hash passwords with argon2id through argon2-cffi, using the library's recommended parameters.
- Enforce at least 12 characters with letters, numbers and symbols (FR-1.7).
- Lock an account for 15 minutes after 5 consecutive failures (FR-1.7). Log every failure.
- Show the same message for an unknown User ID, a wrong password and a locked account, so login never reveals which accounts exist.
- Make session tokens 32 random bytes from `secrets.token_urlsafe`, and store only their SHA-256 hash.
- Rotate the session token at login and after MFA.
- Set cookies with `HttpOnly`, `Secure`, `SameSite=Lax` and `Path=/`, with no `Domain` attribute.
- Require MFA for Admin, Reviewer and Approver (FR-2.8), with TOTP secrets encrypted using a key from the environment.
- Make password reset and set-password tokens single-use, store them hashed, and expire them after 60 minutes.

### Access control

- Every route declares its allowed login types with `require_login_type()`, or is marked `public_route`. A route with neither fails a CI test that lists all routes.
- Every query for items, files, experts or listings goes through the visibility functions. Never filter by hand in a route.
- Return 404, not 403, when an anonymous visitor or Member asks for something they cannot see, so the response never confirms it exists.
- Default to the most restrictive tier when classification is missing (SRS 5.3).

### Input, output and files

- Validate all input with Pydantic schemas, including length limits on every text field.
- Keep Jinja autoescaping on. Never use `|safe` or `Markup()` on user-supplied text.
- Check uploads by extension, sniffed type and size, then scan with ClamAV, before anyone else can open them.
- Use generated storage keys, never user file names, and send user file names only in `Content-Disposition`.
- Send `X-Content-Type-Options: nosniff` with every response.

### Security headers

Nginx sets these on every response:

| Header | Value |
| --- | --- |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; worker-src 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; base-uri 'self'` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |

Restricted pages and files also send `Cache-Control: private, no-store`.

### Data protection

- Use TLS 1.2 or later only.
- Encrypt Restricted and internal files at rest with disk encryption on the storage data disk (D-14), and encrypt database and backup disks.
- Keep all data, including backups, in India (SRS 5.3).
- Store IP addresses in activity logs as a salted SHA-256 hash. Audit events keep the raw IP for incident reporting.
- Show a privacy notice wherever personal data is collected: registration, the expert entry form and notification email settings.

### Logging and monitoring

- Log authentication events, access denials, administrative actions, workflow transitions, scan results, rate-limit hits and setting changes.
- Never log passwords, tokens, one-time codes, TOTP secrets or file contents.
- Keep audit events for at least 3 years, with the latest 180 days searchable online (FR-12.1).
- Keep security logs in India for at least 180 days, to support CERT-In directions. Confirm the current directions with ITPED.
- Alert on repeated lockouts, quarantined files, scanner errors and failed backups.

### Secrets and infrastructure

- Store secrets in environment files on the servers with `600` permissions, separate for each environment, and in the team password manager. Never commit them.
- Rotate secrets when a team member with access leaves.
- Use separate database roles: a migration role that owns the schema, and an application role without DELETE on content tables or UPDATE and DELETE on `audit_event`.
- Expose only ports 443 and 80 to the internet. Port 80 only redirects. Restrict SSH to named keys and known addresses.
- Make internal Nginx locations and the tusd hook endpoints unreachable from outside.

## Definition of Done

A task is Done when:

- [ ] Every acceptance criterion in its spec passes
- [ ] Tests named after the requirement exist and pass in CI (see Testing)
- [ ] CI is green: Ruff, type check, pytest and `pip-audit`
- [ ] The pull request is reviewed and merged, with two reviewers for security-sensitive areas
- [ ] The change is deployed to staging and checked there
- [ ] Any doc this task affects is updated in the same pull request
- [ ] The diff was checked for duplicated code, and anything left is listed in the pull request
- [ ] Every state change it adds writes an audit event
- [ ] The task's journal file (`docs/journal/<CODE>.md`) says Done, with its log and decisions complete
- [ ] The shared planning tracker shows the task as Done, and its totals match the task index
