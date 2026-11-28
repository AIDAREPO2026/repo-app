# Conventions

These rules apply to every task. `AGENTS.md` at the repository root (created in `P0-SET-01`) repeats the coding rules for AI coding tools.

## Task codes, points and status

| Field | Rule |
| --- | --- |
| Code | `Phase-Area-Number`, for example `P2-WF-03` |
| Points | 1, 2, 3, 5, 8 or 13. One point is about half a developer day with AI-assisted coding |
| Role | `Dev`, `Dev A` or `Dev B` (Phase 3 work streams), `QA`, or `ITPED` |
| Status | Not started, In progress, In review, Blocked, Done. Kept only in the task's journal file, `docs/journal/<CODE>.md` |

Split any task of 8 points or more into sub-tasks before starting it. Name them by suffix: `P5-VIEW-01a`, `P5-VIEW-01b`.

**Area codes:** GOV governance, OPS operations, SET setup, ARC architecture, SEC security, ACC accounts, AUD audit, UI interface, CON content, UPL upload, WF workflow, END AIDA Endorsed, VIEW viewing, LIST listings, SRCH search, PUB public, EXP experts, GAL Gallery, KPI metrics, A11Y accessibility, PERF performance, FIX defects, DOC documentation, REL release, QA testing, LIFE lifecycle, NOT notifications, REP reporting, PIL pilot, TRN training.

## Definition of Ready

A task can start when:

- Every task in its **Depends on** list is Done, or the tech lead agrees to work in parallel
- Its acceptance criteria are clear to the developer who picks it up
- Any open decision it relies on is confirmed in [decisions.md](decisions.md)

## Definition of Done

A task is Done when:

- [ ] Every acceptance criterion in its spec passes
- [ ] Tests named after the requirement exist and pass in CI (see Testing)
- [ ] CI is green: Ruff, type check, pytest and `pip-audit`
- [ ] The pull request is reviewed and merged, with two reviewers for security-sensitive areas
- [ ] The change is deployed to staging and checked there
- [ ] Any doc this task affects is updated in the same pull request
- [ ] Every state change it adds writes an audit event
- [ ] The task's journal file (`docs/journal/<CODE>.md`) says Done, with its log and decisions complete
- [ ] The shared planning tracker shows the task as Done, and its totals match the task index

## Task journal

Every task that has started has its own file in [docs/journal/](journal/README.md), named after its code. It is the single home for the task's status, owner, branch, pull request, dated log, decisions and blockers. The planning tracker is a summary refreshed from it.

- Create the file from `docs/journal/_template.md` as the first commit on the task branch.
- Update it in the same pull request as the code: a log line per working session, every decision or deviation from the spec, and the status.
- Set `In review` when the pull request opens, and `Done` in the pull request itself before it merges.
- Coming back to a task later, even after it is Done: any change that belongs to it (review fix, bug fix, follow-up, refactor, a `DEF-###` against it) adds a log line, and any new decision, to that task's journal file in the same pull request. Set it back to `In progress` if the change reopens its acceptance criteria. A change touching several tasks updates each of their files.
- CI refuses a pull request when the task code in its branch name, or at the start of any commit subject, has no change to that task's journal file (`P0-OPS-03`).
- Run `uv run python scripts/build_task_index.py` after changing it, so the task index shows the new status.
- Keep the [shared planning tracker](https://claude.ai/artifact/LnUnS1xkX7cgrTGuwDgY7q) in step with the repository. When a pull request changes a task's status, adds, removes or re-scopes a task, changes its points or dependencies, or adds or changes a decision (`D-##`) or open question (`Q-##`), update the matching rows and totals in the tracker when the pull request opens and again when it merges, and note it in the journal log line. Change the repository first and copy to the tracker, never the other way round.

## Git workflow

One task, one branch, one pull request. Never commit to `main` directly.

| Item | Format | Example |
| --- | --- | --- |
| Branch | `type/<task-code-lowercase>-short-description` | `feat/p1-acc-04-password-lockout` |
| Commit subject | `<CODE>: imperative summary`, under 72 characters, no full stop | `P1-ACC-04: Lock account after five failed sign-ins` |
| Pull request title | `<CODE> Short description` | `P1-ACC-04 Password policy and lockout` |

`type` is one of `feat`, `fix`, `chore`, `docs`, `refactor` or `test`.

The pull request body must contain Summary, Changes, How to test, and Risks or shortcuts. It must also contain a short self-review:

1. **Drift:** does the change match the task spec, these docs and existing patterns?
2. **Duplication:** is any logic copied from elsewhere? Move it into one shared function.
3. **Readability:** is any function long or hard to follow? Simplify it.
4. **Docs:** are the affected docs, the journal and the shared planning tracker updated?

Do not use `--no-verify`, force-push a shared branch or merge your own pull request. Commit messages and pull requests must not contain AI attribution lines.

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
| List records in a table | `data_table()` in `templates/macros/ui.html` (search, fixed header, fits the screen height, row count) | `P1-UI-02` |
| Put a page's actions beside the breadcrumbs | `{% block page_actions %}` in a page that extends `templates/base.html` (see `accounts/admin_discoms.html`) | `P1-UI-02` |
| Render a sign-in, registration or other page shown before signing in | Extend `templates/layouts/auth.html` and start with `auth_heading()` | `P1-UI-02` |

**Avoid hidden behaviour**

- Do not use event listeners that change data behind the caller's back, such as SQLAlchemy events for business rules.
- Do not use global mutable state.
- Do not use magic dependency chains that hide what a route needs.

**Configuration**

- Values the SRS says Admin can change live in the `app_setting` table and are read through `get_setting()`. See the settings table in [architecture.md](architecture.md).
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

**UI and motion rules**

The `apple-design` skill in `.claude/skills/` is the reference for look and feel. These rules decide what applies here, and win over the skill in any conflict.

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

Only the libraries listed in [architecture.md](architecture.md) are approved. To add another, get tech lead approval and add it to that list in the same pull request.

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

## Defects

| Severity | Meaning | Rule |
| --- | --- | --- |
| S1 | Security exposure, data loss or the system is unusable | Fix before any release |
| S2 | A Must requirement fails with no workaround | Fix before release |
| S3 | A requirement fails with a workaround | Fix or defer with tech lead approval |
| S4 | Cosmetic | Defer if needed |

Defect codes are `DEF-###`. Each defect names the task code or acceptance criterion it breaks.
