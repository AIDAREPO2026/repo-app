# Phase 6: Independent assurance

**Dates:** 25 January to 26 February 2027 · **Tasks:** 7 · **Points:** 49 (Dev 41, QA 8)

**Goal:** an independent reviewer confirms the system is secure, and it is proven to meet the SRS performance, accessibility and recovery targets. Restricted content may go live only after `P6-SEC-02`.

These dates depend on when the independent reviewer is available. Book the reviewer during Phase 5.

**Exit criteria**

- [ ] GL-08 to GL-12 pass
- [ ] The independent reviewer confirms all critical and high findings are closed

---

### P6-SEC-01 — Support the independent review against OWASP Top 10 and ASVS Level 2

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P5-QA-02` | SRS 5.3, [security.md](../security.md) release gates |

**Goal:** the independent reviewer has everything needed to test the system thoroughly.

**Scope**

- Prepare a test environment that matches production, with seeded test data and one account per role, including privileged accounts with test TOTP secrets.
- Provide the reviewer with: the architecture and security docs, the route list, the threat and control table, the previous ZAP reports, and read access to the code.
- Fill in an ASVS Level 2 self-assessment for each requirement: met, not applicable, or gap, with evidence.
- Answer the reviewer's questions within one working day.

**Security**

- The review environment uses only test data. Credentials are shared through a password manager, never by email or chat.
- Access is removed when the review ends.

**Acceptance criteria**

- [ ] The ASVS Level 2 self-assessment is complete
- [ ] The reviewer confirms they have what they need and delivers a findings report

**Tests:** none.

---

### P6-SEC-02 — Close all critical and high findings

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 13 | Dev | `P6-SEC-01` | SRS 5.3, GL-08 |

**Goal:** every critical and high finding is fixed, and the reviewer confirms it.

**Scope**

- Raise each finding as a `DEF-###` defect, with critical and high as S1 or S2.
- Fix each with a regression test, and a second reviewer for security-sensitive areas.
- Ask the reviewer to retest, and record their confirmation.
- Plan medium and low findings into maintenance, with dates.

**Security**

- Once this task is Done, Restricted content may be hosted on production. Record the date in [decisions.md](../decisions.md).

**Acceptance criteria**

- [ ] The reviewer confirms in writing that all critical and high findings are closed (GL-08)

**Tests:** a regression test per finding.

---

### P6-PERF-01 — Run the formal load test with Gallery video and report to ITPED

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | Dev | `P5-QA-02` | SRS 5.1, GL-09 |

**Goal:** proof that production-sized infrastructure carries the SRS load, including peak video streaming.

**Scope**

- Extend the `P4-PERF-01` Locust script with Gallery video streaming, SCORM launches and the KPI dashboard.
- Run 350 Member and 200 visitor sessions for 60 minutes on an environment sized like production, including a peak where a quarter of users stream video.
- Tune Gunicorn workers, database connections, indexes and Nginx buffering as needed, and re-run.
- Write a report with targets, results, changes made and recommended production sizing. ITPED signs it.

**Security**

- Run on the test environment only, never production.

**Acceptance criteria**

- [ ] p95 page and search times are under 3 seconds with no errors at full load
- [ ] ITPED signs the report (GL-09)

**Tests:** `tests/load/locustfile.py`.

---

### P6-A11Y-01 — Complete the WCAG 2.1 Level AA audit and fixes

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | Dev | `P5-QA-02` | SRS 5.5, GL-10 |

**Goal:** the portal meets WCAG 2.1 Level AA, including what automated tools cannot detect.

**Scope**

- Run a manual audit against every WCAG 2.1 AA success criterion on each page type, with NVDA on Windows and VoiceOver on macOS, keyboard only, 200% zoom and 320 px width.
- Check videos for captions or transcripts. Provider-supplied videos without captions need a transcript before publication. Add that to the Reviewer checklist.
- Fix every failure, and write an accessibility statement page.

**Security**

- None beyond the standard rules.

**Acceptance criteria**

- [ ] The audit report shows every AA criterion passed or not applicable (GL-10)
- [ ] The accessibility statement is published

**Tests:** extend `tests/e2e/test_accessibility.py` to every new page.

---

### P6-OPS-01 — Rehearse disaster recovery within the 8-hour RTO

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 5 | Dev | `P4-OPS-01`, `P4-DOC-01` | SRS 5.4, GL-11 |

**Goal:** proof that the whole service can be rebuilt from backups within 8 hours.

**Scope**

- Assume the production server is lost. On a fresh server in India, using only the runbook, the repository and the backups:
    1. Provision the server.
    2. Restore the database and the files.
    3. Deploy the current release.
    4. Point a test domain at it, and check login, search, viewing and downloads.
- Time each step against the 8-hour Recovery Time Objective.
- Update the runbook with anything that was missing or wrong.

**Security**

- Secrets come from the password manager. Rotate any secret exposed during the rehearsal.

**Acceptance criteria**

- [ ] Full recovery completes within 8 hours (GL-11), and the runbook is updated

**Tests:** the rehearsal record.

---

### P6-OPS-02 — Configure monitoring against the 99.5% availability target

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 2 | Dev | `P4-OPS-02` | SRS 5.4, GL-12 |

**Goal:** the team knows when the portal is down or degrading, before users report it.

**Scope**

- An external uptime check on `/healthz` and the home page every minute, from outside the hosting provider, with alerts by email and SMS to the on-call contacts.
- Alerts for disk over 80%, a failed nightly backup, a ClamAV signature update older than 48 hours and Celery queue backlog.
- A monthly availability figure for the KPI dashboard.

**Security**

- `/healthz` returns only `ok` or `fail`, with no version or dependency detail.

**Acceptance criteria**

- [ ] Stopping the app on staging raises an alert within 5 minutes (GL-12)

**Tests:** the alert test record.

---

### P6-QA-01 — Retest all assurance fixes

| Points | Role | Depends on | References |
| --- | --- | --- | --- |
| 8 | QA | `P6-SEC-02`, `P6-PERF-01`, `P6-A11Y-01` | GL-08 to GL-12 |

**Goal:** fixes from the review, load test and audit work, and broke nothing else.

**Scope**

- Retest every finding fixed in Phase 6.
- Run full regression, including the sentinel and direct-URL scans.
- Confirm GL-08 to GL-12 with evidence.

**Security**

- Re-run the authenticated ZAP scan, and confirm no new high finding.

**Acceptance criteria**

- [ ] GL-08 to GL-12 pass, and AC-01 to AC-22 still pass

**Tests:** the retest and regression record.
