# Conventions

These rules apply to every task. `AGENTS.md` at the repository root (created in `P0-SET-01`) repeats the coding rules for AI coding tools.

## Task codes, points and status

| Field | Rule |
| --- | --- |
| Code | `Phase-Area-Number`, for example `P2-WF-03` |
| Points | 1, 2, 3, 5, 8 or 13. One point is about half a developer day with AI-assisted coding |
| Role | `Dev`, `Dev A` or `Dev B` (Phase 3 work streams), `QA`, or `ITPED` |
| Status | Not started, In progress, In review, Blocked, Done |

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
- [ ] Status is set to Done in the planning tracker

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
4. **Docs:** are the affected docs updated?

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
| Read a configurable setting | `app.core.settings_store.get_setting()` | `P0-SET-02` |
| Check who may see or open an item | `app.content.visibility` functions | `P2-CON-06` |
| Change a workflow state | `app.workflow.service.apply_action()` | `P2-WF-01` |
| Require a login type on a route | `app.accounts.guards.require_login_type()` | `P1-ACC-08` |
| Verify a CAPTCHA | `app.core.captcha.verify()` | `P1-ACC-02` |
| Send an email | `app.core.email.send_email()` | `P1-ACC-03` |
| Create a notification | `app.workflow.notifications.notify()` | `P2-WF-05` |
| Serve a protected file | `app.content.delivery.protected_file_response()` | `P3-VIEW-03` |
| Render a button, card, badge, modal or other UI element | `templates/macros/ui.html` and the tokens in `static/css/tokens.css` | `P1-UI-02` |

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
- Animate only `transform` and `opacity`, for 150 to 300 ms. Motion must never delay content: the page renders first and motion adds polish.
- Use CSS transitions and the View Transitions API (`hx-swap="... transition:true"` for HTMX swaps). Spring or animation libraries need tech lead approval and are only for real gesture features.
- Do not add drag, flick or rubber-band physics, sound or haptics to the web portal.
- Open and close modals, drawers and menus along the same path, and from the control that opened them.
- Use translucent glass (`backdrop-filter`) only for the top bar and modal scrims. Text on it must pass WCAG AA contrast, with a solid fallback.
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
