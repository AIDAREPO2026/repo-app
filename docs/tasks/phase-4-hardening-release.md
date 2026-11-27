# Phase 4: Hardening and release

**Dates:** 11 to 17 December 2026 · **Tasks:** 19 · **Points:** 49 (Dev 37, QA 12)

**Goal:** the MVP is tested, scanned, documented, recoverable and released on 17 December 2026.

Features are frozen. Only `P4-PUB-01`, `P4-PUB-02` and `P4-KPI-01` add behaviour, and they must be merged by 14 December so regression and UAT test the final build.

**Daily plan**

| Day | Work |
| --- | --- |
| 11 Dec | `P4-PUB-01`, `P4-PUB-02`, `P4-KPI-01`, `P4-SEC-01` scan starts, `P4-SEC-02` starts, `P4-OPS-01`, `P4-QA-01` starts |
| 12 to 14 Dec | `P4-PERF-01`, `P4-A11Y-01`, `P4-FIX-01`, `P4-OPS-02`, `P4-DOC-01`, `P4-DOC-02`, `P4-CON-01`, `P4-QA-02` starts |
| 15 Dec | `P4-FIX-02`, retests, `P4-QA-03` |
| 16 Dec | `P4-REL-01` demonstration to ITPED |
| 17 Dec | `P4-REL-02` release |

**Exit criteria**

- [ ] Every MVP acceptance criterion AC-01 to AC-22 passes, and `P4-QA-03` records the sign-off
- [ ] No open S1 or S2 defect, and no open high ZAP finding
- [ ] Backup restore has been rehearsed, and the rollback steps have been tried on staging
- [ ] Only Public or test content is live (Restricted content waits for `P6-SEC-02`)

---

### P4-PUB-01 — Add the anonymous download limit with CAPTCHA

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P3-VIEW-03`, `P1-ACC-02` | FR-13.7, [security.md](../security.md) bot abuse |

**Goal:** a bot cannot bulk-download public files, while normal visitors are not bothered.

**Scope**

- In `protected_file_response()`, for visitors only, increment a Redis counter `dl:{ip_hash}:{yyyymmddhh}` with a one-hour expiry.
- When the count passes `anon_downloads_per_hour` (default 50), show a CAPTCHA page instead of the file. A solved CAPTCHA, checked with `app.core.captcha.verify()`, allows 50 more downloads for that hour.
- Members are never limited.

**Security**

- Use the same salted IP hash as `P3-LIST-02`.
- If Redis is down, fail open for downloads, and log a warning. Downloads are public files, and blocking them is worse than a short gap in limiting.

**Acceptance criteria**

- [ ] The 51st anonymous download in an hour shows the CAPTCHA (AC-21)
- [ ] After a correct CAPTCHA, downloads continue
- [ ] Changing the setting changes the limit without a deployment

**Tests:** `test_fr_13_7_limit_triggers_captcha`, `test_fr_13_7_captcha_unlocks`, `test_fr_13_7_members_not_limited`.

---

### P4-PUB-02 — Log anonymous and Member activity separately

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P3-LIST-02`, `P3-SRCH-01` | FR-13.8 |

**Goal:** ITPED can tell how much use comes from visitors and how much from Members.

**Scope**

- Make sure `view_event`, `download_event` and `search_log` all set `actor_kind` to `visitor`, `member` or `privileged`.
- Add an index on `(actor_kind, at)` to each table.
- Add a simple Admin page showing views, downloads and searches for the last 30 days, split by `actor_kind`.

**Security**

- The page shows totals only, never IP hashes or session IDs.

**Acceptance criteria**

- [ ] A visitor download and a Member download appear under different totals
- [ ] Anonymous downloads still increase the item's download count (FR-13.8)

**Tests:** `test_fr_13_8_actor_kind_recorded`, `test_fr_13_8_admin_totals_split`.

---

### P4-KPI-01 — Log views, searches, zero-result searches and turnaround

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P3-SRCH-01`, `P2-WF-01` | FR-11.1, FR-11.2, D-04, D-05 |

**Goal:** the raw data for every system-generated KPI is captured from the MVP onwards, ready for the dashboard in `P5-KPI-01`.

**Scope**

- Confirm views, downloads and searches are recorded (`P3-LIST-02`, `P3-SRCH-01`), including zero-result searches (D-04).
- Add `app/kpi/queries.py` with plain SQL functions for:
    - submissions by Discom and module
    - median and 90th-percentile turnaround from Submitted to Approved, from `workflow_event`
    - number of items returned, rejected and published per month
    - top searches and top zero-result searches
- No dashboard yet. A management command `python -m app.kpi.report --month 2026-12` prints these figures, for checking.

**Security**

- KPI queries respect D-13 by excluding privileged activity.

**Acceptance criteria**

- [ ] Every figure in the report matches a hand count on staging data
- [ ] Turnaround is measured in calendar hours, and the output says so

**Tests:** `test_fr_11_2_turnaround_median`, `test_d04_zero_result_top_list`, `test_fr_11_1_submissions_by_discom`.

---

### P4-SEC-01 — Run OWASP ZAP and the dependency audit, and fix high findings

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | All Phase 3 tasks | SRS 5.3, AC-22, [security.md](../security.md) release gates |

**Goal:** the MVP has no known high-severity weakness when it ships.

**Scope**

- Run an authenticated OWASP ZAP scan on staging, once as a Member and once as Admin, using a ZAP context that logs in, handles MFA with a test TOTP secret, and keeps the CSRF token.
- Run an unauthenticated scan as a visitor.
- Run `uv run pip-audit` against the `uv.lock` environment and `trivy image` on the built images.
- Fix every high finding. Record medium and low ones as `DEF-###` with a planned phase.
- Save the reports in `security/reports/2026-12/`.

**Security**

- Scan staging only, never production.
- Test credentials come from the staging seed, not from a real user.

**Acceptance criteria**

- [ ] No high ZAP, pip-audit or Trivy finding remains open (AC-22)
- [ ] Reports and the triage list are attached to the task

**Tests:** a regression test for every fixed finding where one can be written.

---

### P4-SEC-02 — Human line-by-line review of file delivery and public access

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev (tech lead or security reviewer) | `P3-VIEW-03`, `P3-PUB-02`, `P4-PUB-01` | SRS 5.3, R-04 |

**Goal:** a second person checks the code that lets anyone outside the Discom community reach files and pages.

**Scope**

Review `app/content/delivery.py`, `app/public/`, `app/search/service.py`, the Nginx configuration and `app/experts/` against this checklist:

- [ ] Every file route calls `protected_file_response()`
- [ ] No storage URL, storage key or file name reaches a visitor for a Restricted item
- [ ] Teaser views use `ItemTeaserView` only
- [ ] Flag-No items return 404 and are excluded from counts
- [ ] Every non-public route is listed in the route registry test and returns 404 to visitors
- [ ] Rate limits are set for login, registration, search, email reveal and downloads
- [ ] Security headers match [security.md](../security.md)
- [ ] Expert emails are never in page source

**Security**

- S1 and S2 findings are fixed before `P4-QA-03`.

**Acceptance criteria**

- [ ] The completed checklist and findings are attached to the review pull request
- [ ] No S1 or S2 finding remains open

**Tests:** add a regression test for every defect found.

---

### P4-PERF-01 — Run an indicative load test at 350 Member and 200 visitor sessions

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | All Phase 3 tasks | SRS 5.1 |

**Goal:** an early check that the MVP can carry the expected load, so problems surface before the formal test in `P6-PERF-01`.

**Scope**

- A Locust script in `tests/load/` with two user types:
    - Member: log in, open the dashboard, search, open items, download
    - Visitor: home page, search, public item, download
- Run 350 Member and 200 visitor sessions on staging for 20 minutes.
- Record p50 and p95 response times, error rate, and CPU and memory per container.
- Target: p95 under 3 seconds for pages and searches (SRS 5.1), and no errors.
- Fix quick wins, such as missing indexes or N+1 queries. List the rest for Phase 6.

**Security**

- Run against staging only. Load-test accounts are created by the seed and deleted afterwards.

**Acceptance criteria**

- [ ] The report states p50, p95 and error rate for each user type
- [ ] Any page over 3 seconds at p95 has a defect raised

**Tests:** `tests/load/locustfile.py`.

---

### P4-A11Y-01 — Run automated accessibility checks and fix issues

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 3 | Dev | All Phase 3 tasks | SRS 5.5, WCAG 2.1 AA |

**Goal:** the MVP has no automatically detectable WCAG 2.1 AA failures on its main pages.

**Scope**

- Add axe-core checks to the Playwright suite for: public home, module listing, search results, public item, teaser, login, registration, Member dashboard, submission form, each privileged queue and the item review page.
- Fix every serious and critical violation.
- Check keyboard-only use of login, search, submission and the workflow actions.

The full manual audit is `P6-A11Y-01`.

**Security**

- None beyond the standard rules.

**Acceptance criteria**

- [ ] axe-core reports no serious or critical violations on the listed pages
- [ ] Login, search, submission and approval can be completed by keyboard only

**Tests:** `tests/e2e/test_accessibility.py`.

---

### P4-OPS-01 — Set up backups and rehearse a restore

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P0-OPS-02` | SRS 5.4, AC-22 |

**Goal:** data can be recovered if the database or storage is lost.

**Scope**

- A nightly `pg_dump -Fc` from a backup container, encrypted, written to a separate storage bucket in India, kept for 30 days.
- A nightly copy of `$DATA_DIR/seaweedfs`, or of the bucket through S3, to the backup storage (D-14).
- A restore script `deploy/restore.sh` that restores a named dump into a fresh database.
- Rehearse: restore last night's backup to a scratch environment, start the app against it, log in and open an item. Record the time taken.

**Security**

- The backup bucket has its own credentials, and the application cannot delete from it.
- Backups are encrypted at rest.

**Acceptance criteria**

- [ ] A restore from backup works and is timed (AC-22)
- [ ] The steps are written in the runbook (`P4-DOC-01`)

**Tests:** the rehearsal record attached to the task.

---

### P4-OPS-02 — Prepare release deployment and rollback steps

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P0-OPS-02` | SRS 5.6 |

**Goal:** the release can be deployed and, if needed, rolled back in minutes.

**Scope**

- Provision the production server with the same Docker Compose files as staging, with production secrets from the environment.
- A `deploy/release.sh` script that:
    1. Takes a database backup.
    2. Pulls the tagged images.
    3. Runs `alembic upgrade head`.
    4. Restarts the services with `docker compose --env-file .env ... up -d`. It never uses `down -v`.
    5. Runs a smoke check on `/healthz` and the home page.
- A `deploy/rollback.sh` script that redeploys the previous image tag. If a migration cannot be reversed, it restores the pre-release backup.
- Try both scripts on staging.

**Security**

- Production secrets are never in the repository or in the images.
- Only the tech lead and one named deputy can run the release.
- The scripts refuse to run when `DATA_DIR` is not set, so a server never falls back to keeping data inside the repository folder.

**Acceptance criteria**

- [ ] A release and a rollback have each been run on staging
- [ ] Production is provisioned and reachable over HTTPS with the same TLS and header setup as staging

**Tests:** the staging release and rollback record.

---

### P4-DOC-01 — Write the operations runbook, first version

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P4-OPS-01`, `P4-OPS-02` | SRS 5.8, [security.md](../security.md) incident response |

**Goal:** someone other than the author can run, recover and respond to incidents on the MVP.

**Scope**

`docs/runbook.md` covering:

- services and what each one does
- starting, stopping and checking health
- logs: where they are and how to search them
- release and rollback
- backup and restore
- rotating secrets, including `FERNET_KEY` and database passwords
- clearing a ClamAV signature problem and re-queuing scans
- unlocking a locked account, and resetting MFA for a privileged user
- incident response: who to call, how to preserve logs, reporting to CERT-In within 6 hours, and DPDP notification. Confirm the current CERT-In rule before go-live.
- named contacts for ITPED and the development team

**Security**

- The runbook contains no secrets, only where to find them.

**Acceptance criteria**

- [ ] A developer who did not write it can restore a backup using only the runbook

**Tests:** none.

---

### P4-DOC-02 — Write role quick guides, stating the 20 MB image limit

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | All Phase 3 tasks | SRS 5.8, D-01 |

**Goal:** each user type can do its job without training.

**Scope**

One- or two-page guides, in `docs/guides/`, with screenshots:

- Member: register, log in, submit, track, respond to a return
- Admin: activate Discoms, triage submissions, edit, forward, manage tags, manage experts and Gallery, bulk import
- Reviewer: review, set the teaser flag, return, forward
- Approver: approve, reject, return, apply AIDA Endorsed

Each guide states the file limits, including "Images must be 20 MB or smaller" (D-01).

**Security**

- The guides tell privileged users never to share the TOTP device, and Members never to share the Discom password outside the Discom.

**Acceptance criteria**

- [ ] All four guides exist, and ITPED has reviewed them
- [ ] Each guide states the 20 MB image limit

**Tests:** none.

---

### P4-CON-01 — Load Public or test content through bulk import

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P2-CON-07` | SRS 6.2 |

**Goal:** the MVP has enough content to be demonstrated and tested.

**Scope**

- Use the bulk importer to load at least one Public or clearly marked test item per subcategory, plus 2 test expert profiles and 1 test Gallery listing.
- Run them through the workflow to Approved.

**Security**

- No real Restricted content is loaded until `P6-SEC-02` is Done.

**Acceptance criteria**

- [ ] Every subcategory shows at least one item on staging and production

**Tests:** none.

---

### P4-FIX-01 — Fix defects from regression testing

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P4-QA-01` (ongoing) | SRS Section 8 |

**Goal:** defects found in regression are fixed in priority order.

**Scope**

- Fix S1 and S2 defects first, then S3 as time allows.
- Each fix follows the normal branch, test and review process, with a regression test.

**Security**

- Security defects are always at least S2.

**Acceptance criteria**

- [ ] No open S1 or S2 regression defect by 15 December

**Tests:** a regression test per fix.

---

### P4-FIX-02 — Fix defects from UAT scenarios

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P4-QA-02` (ongoing) | SRS Section 8 |

**Goal:** defects found in UAT are fixed before sign-off.

**Scope**

- As in `P4-FIX-01`, for UAT defects.

**Security**

- As in `P4-FIX-01`.

**Acceptance criteria**

- [ ] No open S1 or S2 UAT defect by the end of 15 December

**Tests:** a regression test per fix.

---

### P4-QA-01 — Run full regression

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | QA | All Phase 3 tasks | SRS Section 8, AC-21 |

**Goal:** everything built in Phases 1 to 4 still works together.

**Scope**

- Run the full automated suite and every `tests/e2e/` scenario on staging.
- Manually test the anonymous download limit (AC-21).
- Raise defects for `P4-FIX-01`, and retest fixes.

**Security**

- Re-run the direct-URL and sentinel scans from `P3-QA-02`.

**Acceptance criteria**

- [ ] All automated tests pass, and AC-21 passes

**Tests:** the regression run record.

---

### P4-QA-02 — Run in-scope UAT scenarios

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | QA | `P4-CON-01` | SRS Section 8 |

**Goal:** ITPED's representatives confirm the MVP does what they need.

**Scope**

- Walk through each role's scenario from the quick guides with ITPED staff, using test accounts.
- Record each scenario as passed or failed, with defects raised for `P4-FIX-02`.

**Security**

- UAT uses test accounts and Public or test content only.

**Acceptance criteria**

- [ ] Every in-scope scenario passes or has an accepted workaround

**Tests:** the UAT record.

---

### P4-QA-03 — Complete the MVP acceptance sign-off

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | QA | `P4-QA-01`, `P4-QA-02`, `P4-SEC-01`, `P4-SEC-02`, `P4-OPS-01` | [acceptance.md](../acceptance.md) |

**Goal:** a single record shows every MVP criterion has passed.

**Scope**

- Fill in AC-01 to AC-22 with the evidence (test run, screenshot or record) and the date.
- List open S3 and S4 defects as known issues for the release notes.

**Security**

- Confirm the release gates in [security.md](../security.md) are met.

**Acceptance criteria**

- [ ] Every AC passes, and the record is signed by the QA lead and the tech lead

**Tests:** none.

---

### P4-REL-01 — Demonstrate the MVP to ITPED on 16 December

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P4-QA-03` | SRS Section 8 |

**Goal:** ITPED sees the MVP working end to end and agrees to the release.

**Scope**

- A scripted demonstration: register a Discom, activate it, submit, review, approve, find through search, view as a visitor, and show the audit log.
- Record ITPED's go or no-go and any conditions.

**Security**

- Use test accounts. Do not show real credentials or TOTP secrets on screen.

**Acceptance criteria**

- [ ] ITPED gives a recorded go decision

**Tests:** none.

---

### P4-REL-02 — Release the MVP on 17 December with release notes

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 1 | Dev | `P4-REL-01`, `P4-OPS-02` | SRS Section 8 |

**Goal:** the MVP is live on production.

**Scope**

- Tag `v0.1.0`, run `deploy/release.sh`, and run the smoke check.
- Publish release notes: what is included, known issues, the Public-or-test-content-only rule, and what comes in Phase 5.
- Create the real Admin, Reviewer and Approver accounts with MFA enrolled in person or by video call.

**Security**

- Remove all test accounts and test secrets from production.
- Confirm production `DEBUG` is off and the Content Security Policy is in force.

**Acceptance criteria**

- [ ] Production serves the tagged release, and the smoke check passes
- [ ] Release notes are shared with ITPED

**Tests:** the smoke check.
